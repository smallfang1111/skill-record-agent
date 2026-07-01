#!/usr/bin/env python3
"""
FastAPI 后端服务

封装 src.agent 模块，提供 REST API 接口
"""

import sys
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
    read_memory_index
)
from src.agent.tools import create_learning_plan, update_progress
from src.agent.core import agent_loop

# 导入数据存储模块
from src.data.skills import load_skills, create_skill, update_step, update_note, delete_skill, save_skills, get_timeline
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
            note=progress.note or ''
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


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """与 AI 助手对话（基于会话）"""
    try:
        # 保存用户消息到会话
        add_message_to_session(req.session_id, "user", req.message)
        
        # 使用 agent_loop 处理对话
        messages = [{"role": "user", "content": req.message}]
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
    """删除技能"""
    try:
        delete_skill(skill_id)
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
