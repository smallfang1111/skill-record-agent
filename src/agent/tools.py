"""
工具模块

定义 agent 可以使用的所有工具：
- 基础工具：bash, read_file, write_file, edit_file, glob
- 子代理工具：task (spawn_subagent)
- 学习管家专用工具：create_learning_plan, update_progress

同时提供工具定义（TOOLS）和工具处理器（TOOL_HANDLERS）。
"""

import os
import subprocess
import json
import glob as glob_module
from pathlib import Path
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# 配置
WORKDIR = Path.cwd()
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"


def _get_client():
    """延迟获取 Anthropic 客户端"""
    return Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        base_url=os.environ.get("ANTHROPIC_BASE_URL") or None
    )


def _get_model():
    """延迟获取模型名称"""
    return os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")


# ═══════════════════════════════════════════════
# 基础工具
# ═══════════════════════════════════════════════

def safe_path(p: str) -> Path:
    """确保路径在工作目录内（防止路径遍历攻击）"""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


def run_bash(command: str) -> str:
    """运行 shell 命令"""
    try:
        r = subprocess.run(
            command, shell=True, cwd=WORKDIR,
            capture_output=True, text=True, timeout=120,
            encoding='utf-8', errors='replace'
        )
        stdout = r.stdout or ""
        stderr = r.stderr or ""
        out = (stdout + stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int | None = None) -> str:
    """读取文件内容"""
    try:
        lines = safe_path(path).read_text(encoding='utf-8').splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """写入文件内容"""
    try:
        file_path = safe_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """替换文件中的精确文本（仅替换第一次出现）"""
    try:
        file_path = safe_path(path)
        text = file_path.read_text(encoding='utf-8', errors='replace')
        if old_text not in text:
            return f"Error: text not found in {path}"
        file_path.write_text(text.replace(old_text, new_text, 1), encoding='utf-8')
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_glob(pattern: str) -> str:
    """查找匹配 glob 模式的文件"""
    try:
        results = []
        for match in glob_module.glob(pattern, root_dir=WORKDIR):
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR):
                results.append(match)
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


def extract_text(content) -> str:
    """从 Anthropic SDK 的 content 块中提取文本"""
    if not isinstance(content, list):
        return str(content)
    return "\n".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text")


# ═══════════════════════════════════════════════
# 子代理工具
# ═══════════════════════════════════════════════

SUB_SYSTEM = (
    f"You are a coding agent at {WORKDIR}. "
    "Complete the task you were given, then return a concise summary. "
    "Do not delegate further."
)

SUB_TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
]

SUB_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write
}


def spawn_subagent(task: str) -> str:
    """启动子代理处理子任务"""
    print(f"\n\033[35m[Subagent spawned]\033[0m")
    messages = [{"role": "user", "content": task}]
    for _ in range(30):
        response = _get_client().messages.create(
            model=_get_model(), system=SUB_SYSTEM,
            messages=messages, tools=SUB_TOOLS, max_tokens=8000
        )
        
        # 添加这几行来查看缓存命中情况
        print(response.usage,'5')
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            break
        results = []
        for block in response.content:
            if block.type == "tool_use":
                handler = SUB_HANDLERS.get(block.name)
                output = handler(**block.input) if handler else f"Unknown: {block.name}"
                print(f"  \033[90m[sub] {block.name}: {str(output)[:100]}\033[0m")
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})

    result = extract_text(messages[-1]["content"])
    if not result:
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                result = extract_text(msg["content"])
                if result:
                    break
        if not result:
            result = "Subagent stopped after 30 turns without final answer."
    print(f"\033[35m[Subagent done]\033[0m")
    return result


# ═══════════════════════════════════════════════
# 学习管家专用工具
# ═══════════════════════════════════════════════

from src.agent.memory import write_memory_file


def create_learning_plan(skill: str, goal: str, steps: list) -> str:
    """为技能创建学习计划，存入记忆系统"""
    steps_text = "\n".join(f"{i+1}. {step}" for i, step in enumerate(steps))
    memory_body = f"""
## {skill} 学习计划
- 目标：{goal}
- 总步骤：{len(steps)}步
- 当前进度：0/{len(steps)}
- 创建时间：{datetime.now().strftime('%Y-%m-%d')}

### 学习步骤：
{steps_text}
"""
    write_memory_file(
        f"learning-plan-{skill}",
        "project",
        f"{skill} 学习计划：{goal}",
        memory_body.strip(),
        skill=skill,
    )
    return f"✅ 已为「{skill}」创建学习计划，共 {len(steps)} 个步骤。\n目标：{goal}"


def update_progress(skill: str, completed: str, note: str = "") -> str:
    """更新学习进度，存入记忆系统"""
    memory_body = f"""
## {skill} 学习进度更新
- 完成内容：{completed}
- 备注：{note}
- 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
    write_memory_file(
        f"progress-{skill}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "user",
        f"{skill} 进度：{completed}",
        memory_body.strip(),
        skill=skill,
    )
    return f"✅ {skill} 进度已更新：{completed}"


# ═══════════════════════════════════════════════
# 工具定义 & 处理器映射
# ═══════════════════════════════════════════════

TOOLS = [
    {"name": "bash", "description": "Run a shell command.",
     "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text in a file once.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files matching a glob pattern.",
     "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "task", "description": "Launch a subagent to handle a subtask.",
     "input_schema": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}},
    {"name": "create_learning_plan", "description": "为某个技能创建学习计划。技能可以是：雅思、AI-Agent、化妆等。",
     "input_schema": {"type": "object", "properties": {"skill": {"type": "string", "description": "技能名称，如'雅思'"}, "goal": {"type": "string", "description": "学习目标，如'考到7分'"}, "steps": {"type": "array", "items": {"type": "string"}, "description": "学习步骤列表"}}, "required": ["skill", "goal", "steps"]}},
    {"name": "update_progress", "description": "更新某个技能的学习进度",
     "input_schema": {"type": "object", "properties": {"skill": {"type": "string", "description": "技能名称"}, "completed": {"type": "string", "description": "刚完成的内容"}, "note": {"type": "string", "description": "备注（可选）"}}, "required": ["skill", "completed"]}},
]

TOOL_HANDLERS = {
    "bash": run_bash,
    "read_file": run_read,
    "write_file": run_write,
    "edit_file": run_edit,
    "glob": run_glob,
    "task": spawn_subagent,
    "create_learning_plan": create_learning_plan,
    "update_progress": update_progress,
}
