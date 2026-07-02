#!/usr/bin/env python3
"""
FastAPI 后端服务

封装 src.agent 模块，提供 REST API 接口
"""

import sys
import os
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 导入 agent 模块
from src.agent.memory import (
    list_memory_files,
    read_memory_file,
    write_memory_file,
    read_memory_index,
    delete_memories_for_skill,
    filter_skill_memories,
)
from src.agent.tools import create_learning_plan, update_progress
from src.agent.core import agent_loop

# 导入数据存储模块
from src.data.skills import load_skills, create_skill, update_step, update_note, delete_skill, save_skills, get_timeline, get_skill
from src.data.chat_sessions import (
    load_sessions, create_session, get_session,
    add_message_to_session, delete_session, get_grouped_sessions
)

# 创建 FastAPI 应用
app = FastAPI(title="学习管家 API", version="1.0.0")

# 配置 CORS（允许前端访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite 默认端口
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════
# 数据模型
# ═══════════════════════════════════════════════

class SkillCreate(BaseModel):
    """创建技能的请求模型"""
    name: str
    goal: str
    steps: List[str]


class ProgressUpdate(BaseModel):
    """更新进度的请求模型"""
    skill_id: str = ""
    skill_name: str = ""
    completed_step: str
    note: Optional[str] = None
    status: Optional[str] = "completed"  # 支持 completed / inprogress 双向切换


class ChatMessage(BaseModel):
    """聊天消息模型"""
    message: str


# ═══════════════════════════════════════════════
# API 路由
# ═══════════════════════════════════════════════

@app.get("/")
async def root():
    """根路径"""
    return {"message": "学习管家 API 正在运行"}


@app.get("/api/memories")
async def get_memories():
    """获取所有记忆文件"""
    try:
        memories = list_memory_files()
        return {"memories": memories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memories/{filename}")
async def get_memory(filename: str):
    """获取单个记忆文件内容"""
    try:
        content = read_memory_file(filename)
        if content is None:
            raise HTTPException(status_code=404, detail="记忆文件不存在")
        return {"filename": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/skills")
async def create_skill_api(skill: SkillCreate):
    """创建学习计划"""
    try:
        skill_data = create_skill(
            name=skill.name,
            goal=skill.goal,
            steps=skill.steps
        )
        return {"message": "技能创建成功", "skill": skill_data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/progress")
async def update_skill_progress(progress: ProgressUpdate):
    """更新学习进度"""
    try:
        skills = load_skills()
        
        # 优先用 skill_id，其次用 skill_name
        skill = None
        if progress.skill_id:
            for s in skills:
                if s['id'] == progress.skill_id:
                    skill = s
                    break
        elif progress.skill_name:
            for s in skills:
                if s['name'] == progress.skill_name:
                    skill = s
                    break
        
        if not skill:
            raise ValueError(f"技能不存在")
        
        updated_skill = update_step(
            skill_id=skill['id'],
            step_id=progress.completed_step,
            note=progress.note or '',
            status=progress.status or 'completed'
        )
        
        return {"message": "进度更新成功", "skill": updated_skill}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class NoteSaveRequest(BaseModel):
    """保存笔记的请求模型"""
    skill_id: str
    step_id: str
    note: str


@app.put("/api/notes")
async def save_note_api(req: NoteSaveRequest):
    """仅保存步骤笔记（不改变完成状态）"""
    try:
        updated_skill = update_note(
            skill_id=req.skill_id,
            step_id=req.step_id,
            note=req.note
        )
        return {"message": "笔记保存成功", "skill": updated_skill}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ChatRequest(BaseModel):
    """聊天请求"""
    session_id: str
    message: str


class SkillUpdate(BaseModel):
    """更新技能的请求模型"""
    name: Optional[str] = None
    goal: Optional[str] = None
    steps: Optional[List[str]] = None


def _build_system_prompt() -> str:
    """读取系统提示词模板，注入用户技能/进度/记忆"""
    # 读取模板
    prompt_path = Path(__file__).parent.parent / "data" / "system_prompt.md"
    if prompt_path.exists():
        template = prompt_path.read_text(encoding='utf-8')
    else:
        template = "# 系统提示词\n你是学习管家助手，帮助用户管理学习计划。"

    # ── 注入技能摘要 ──
    try:
        skills = load_skills()
        if skills:
            lines = []
            for s in skills:
                completed = sum(1 for step in s.get('steps', []) if step.get('status') == 'completed')
                total = len(s.get('steps', []))
                lines.append(f"- {s.get('name', '未命名')}：{s.get('goal', '')}（进度 {completed}/{total}）")
            skills_summary = "\n".join(lines) if lines else "用户还没有创建任何技能。"
        else:
            skills_summary = "用户还没有创建任何技能。"
    except Exception:
        skills_summary = "（无法读取技能数据）"

    # ── 注入记忆摘要 ──
    try:
        memories = filter_skill_memories(list_memory_files())
        if memories:
            # 只取前 3 条最相关的记忆
            mem_lines = [f"- {m.get('name', m.get('filename', ''))}：{m.get('description', '')}" for m in memories[:3]]
            memory_summary = "\n".join(mem_lines)
        else:
            memory_summary = "暂无记忆数据。"
    except Exception:
        memory_summary = "（无法读取记忆数据）"

    # 替换模板变量
    result = template.replace("{skills_summary}", skills_summary)
    result = result.replace("{memory_summary}", memory_summary)
    return result


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """与 AI 助手对话（基于会话）"""
    try:
        # 保存用户消息到会话
        add_message_to_session(req.session_id, "user", req.message)

        # ── 组装系统提示词（注入用户技能/进度） ──
        system_prompt = _build_system_prompt()

        # ── 应用用户配置的 API Key / Base URL / Model ──
        apply_user_settings()

        # 使用 agent_loop 处理对话（带系统提示词）
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": req.message}
        ]
        agent_loop(messages)
        
        # 获取 AI 回复
        response_text = "处理完成，但没有返回消息"
        if messages and messages[-1]["role"] == "assistant":
            content = messages[-1]["content"]
            if isinstance(content, list):
                text = ""
                for block in content:
                    if hasattr(block, 'text'):
                        text += block.text
                response_text = text
            else:
                response_text = str(content)
        
        # 保存 AI 回复到会话
        updated = add_message_to_session(req.session_id, "assistant", response_text)
        
        return {"response": response_text, "session": updated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════
# 会话管理 API
# ═══════════════════════════════════════════════

@app.get("/api/sessions")
async def get_sessions():
    """获取会话列表（按时间分组）"""
    return {"groups": get_grouped_sessions()}


@app.post("/api/sessions")
async def new_session():
    """创建新会话"""
    try:
        session = create_session()
        return {"session": session}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sessions/{session_id}")
async def get_single_session(session_id: str):
    """获取单个会话详情（含消息）"""
    session = get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"session": session}


@app.delete("/api/sessions/{session_id}")
async def remove_session(session_id: str):
    """删除会话"""
    try:
        delete_session(session_id)
        return {"message": "会话已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.delete("/api/skills/{skill_id}")
async def delete_skill_api(skill_id: str):
    """删除技能，并一并清理其关联的记忆文件（保持 AI 上下文与技能管理一致）"""
    try:
        skill = get_skill(skill_id)
        skill_name = (skill.get('name') if skill else '') or ''
        delete_skill(skill_id)
        if skill_name:
            delete_memories_for_skill(skill_name)
        return {"message": "技能已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/skills/{skill_id}")
async def update_skill_api(skill_id: str, update: SkillUpdate):
    """更新技能（编辑名称/目标/步骤）"""
    try:
        skills = load_skills()
        skill = None
        for s in skills:
            if s['id'] == skill_id:
                skill = s
                break
        
        if not skill:
            raise ValueError(f"技能不存在")
        
        # 更新字段
        if update.name is not None:
            skill['name'] = update.name
        if update.goal is not None:
            skill['goal'] = update.goal
        if update.steps is not None:
            # 重新构建步骤（保留已完成的步骤状态）
            old_steps = {step['id']: step for step in skill['steps']}
            new_steps = []
            for i, content in enumerate(update.steps):
                step_id = f"{skill_id}-{i}"
                if step_id in old_steps:
                    new_steps.append(old_steps[step_id])
                else:
                    new_steps.append({
                        'id': step_id,
                        'content': content,
                        'status': 'pending',
                        'note': '',
                        'completedAt': None
                    })
            skill['steps'] = new_steps
        
        skill['updatedAt'] = datetime.now().isoformat()
        save_skills(skills)
        
        return {"message": "技能更新成功", "skill": skill}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/skills")
async def get_skills():
    """获取所有技能"""
    try:
        skills = load_skills()
        return {"skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/timeline")
async def get_timeline_api():
    """获取学习时间线"""
    try:
        events = get_timeline()
        return {"events": events}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# ═══════════════════════════════════════════════
# 设置管理 API
# ═══════════════════════════════════════════════

SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"

class SettingsRequest(BaseModel):
    """设置请求模型"""
    model: str
    api_key: str
    base_url: str
    models: List[str] | None = None
    workspace: str = ""


def _load_settings() -> dict:
    """读取设置（返回默认值如果文件不存在）"""
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {
        "model": os.environ.get("MODEL_ID", ""),
        "api_key": "",
        "base_url": "",
        "models": []
    }


def _save_settings(data: dict) -> None:
    """保存设置到文件"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


@app.get("/api/settings")
async def get_settings():
    """获取当前设置（隐藏 api_key 完整值）"""
    try:
        s = _load_settings()
        # API Key 只显示后 4 位，其余用 * 替代
        key = s.get('api_key', '')
        if len(key) > 4:
            s['api_key'] = '***' + key[-4:]
        elif key:
            s['api_key'] = '****'
        return s
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/settings")
async def save_settings(req: SettingsRequest):
    """保存设置"""
    try:
        # 如果新传入的 key 是脱敏的（以 *** 开头），保留旧值
        existing = _load_settings()
        if req.api_key.startswith('***') or (req.api_key == '****' and not existing.get('api_key', '').startswith('***')):
            actual_key = existing.get('api_key', '')
        else:
            actual_key = req.api_key

        data = {
            "model": req.model,
            "api_key": actual_key,
            "base_url": req.base_url,
            "models": req.models or [],
            "workspace": (req.workspace or "").strip(),
            "updatedAt": datetime.now().isoformat()
        }
        _save_settings(data)
        return {"message": "设置保存成功", "settings": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def apply_user_settings() -> bool:
    """将用户配置写入环境变量，让所有 agent 模块延迟读取时生效"""
    s = _load_settings()
    if not s.get('api_key'):
        return False
    try:
        os.environ['ANTHROPIC_API_KEY'] = s['api_key']
        if s.get('base_url'):
            os.environ['ANTHROPIC_BASE_URL'] = s['base_url']
        if s.get('model'):
            os.environ['MODEL_ID'] = s['model']
        return True
    except Exception:
        return False


@app.on_event("startup")
def _load_settings_on_startup():
    """应用启动时，把已保存的用户配置写入环境变量（这样即使 .env 被隐藏也能用）"""
    apply_user_settings()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
