"""
记忆系统模块

提供跨会话的持久化记忆功能。
记忆存储在 data/memory/ 目录下。

主要功能：
- 读写记忆文件（Markdown + YAML frontmatter）
- 重建记忆索引（MEMORY.md）
- 选择相关记忆注入上下文
- 从对话中提取新记忆
- 合并重复/过期的记忆
"""

import os
import json
import re
import time
from pathlib import Path
from datetime import datetime

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# 配置
from src.data.skills import load_skills as _load_skills_from_store
WORKDIR = Path.cwd()
MEMORY_DIR = WORKDIR / "data" / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"

MEMORY_TYPES = ["user", "feedback", "project", "reference"]


def _get_client():
    """延迟获取 Anthropic 客户端（每次调用都读最新环境变量，支持用户动态配置）"""
    return Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
        base_url=os.environ.get("ANTHROPIC_BASE_URL") or None
    )


def _get_model():
    """延迟获取模型名称"""
    return os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """解析 YAML frontmatter"""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def write_memory_file(name: str, mem_type: str, description: str, body: str, skill: str = ""):
    """写入单个记忆文件（带 YAML frontmatter）。

    skill: 该记忆关联的技能名称（如有）。用于后续按「当前技能集合」过滤，
           避免已删除技能的记忆仍被注入给 AI。
    """
    slug = name.lower().replace(" ", "-").replace("/", "-")
    filename = f"{slug}.md"
    filepath = MEMORY_DIR / filename
    front = (
        f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}"
        + (f"\nskill: {skill}" if skill else "")
        + "\n---\n\n"
    )
    filepath.write_text(front + body + "\n", encoding='utf-8')
    _rebuild_index()
    return filepath


def _rebuild_index():
    """从所有记忆文件重建 MEMORY.md 索引"""
    lines = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        meta, body = _parse_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80])
        lines.append(f"- [{name}]({f.name}) — {desc}")
    try:
        MEMORY_INDEX.write_text("\n".join(lines) + "\n" if lines else "", encoding='utf-8')
    except Exception:
        pass


def _current_skill_names() -> set:
    """返回技能管理里当前存在的技能名称集合"""
    try:
        return {s.get('name', '').strip() for s in _load_skills_from_store() if (s.get('name') or '').strip()}
    except Exception:
        return set()


def _memory_skill(content: str) -> str | None:
    """从记忆内容中解析其关联的技能名称。

    优先读取 frontmatter 的 skill 字段；否则从学习管家专用
    记忆体（学习计划 / 进度更新）的标题中提取。
    无法确定时返回 None（视为与技能无关的通用记忆）。
    """
    meta, body = _parse_frontmatter(content)
    skill = (meta.get('skill') or '').strip()
    if skill:
        return skill
    for line in body.splitlines():
        m = re.match(r'^##\s+(.+?)\s+学习计划', line) or re.match(r'^##\s+(.+?)\s+学习进度更新', line)
        if m:
            return m.group(1).strip()
    return None


def filter_skill_memories(memory_list: list) -> list:
    """过滤掉仅关联「已删除技能」的记忆，只保留与当前技能相关或无关的通用记忆。"""
    current = _current_skill_names()
    out = []
    for m in memory_list:
        skill = _memory_skill(m.get('body', '') or '')
        if skill and skill not in current:
            continue
        out.append(m)
    return out


def read_memory_index() -> str:
    """读取记忆索引（每次 turn 注入到 SYSTEM 提示词中）。

    仅包含与当前技能管理里存在的技能相关的记忆，
    避免 AI 助手提及已被删除的技能。
    """
    files = filter_skill_memories(list_memory_files())
    if not files:
        return ""
    lines = [f"- [{m['name']}]({m['filename']}) — {m['description']}" for m in files]
    return "\n".join(lines)


def read_memory_file(filename: str) -> str | None:
    """读取单个记忆文件的完整内容"""
    path = MEMORY_DIR / filename
    if not path.exists():
        return None
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None


def list_memory_files() -> list[dict]:
    """列出所有记忆文件及其元数据"""
    result = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        meta, body = _parse_frontmatter(raw)
        result.append({
            "filename": f.name,
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
            "type": meta.get("type", "user"),
            "body": body,
        })
    return result


def select_relevant_memories(messages: list, max_items: int = 5) -> list[str]:
    """根据最近对话选择相关的记忆文件名"""
    files = list_memory_files()
    if not files:
        return []

    # 收集最近的用户文本
    recent_texts = []
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    str(getattr(b, "text", "")) for b in content
                    if getattr(b, "type", None) == "text"
                )
            if isinstance(content, str):
                recent_texts.append(content)
            if len(recent_texts) >= 3:
                break
    recent = " ".join(reversed(recent_texts))[:2000]

    if not recent.strip():
        return []

    # 构建记忆目录供 LLM 选择
    catalog_lines = []
    for i, f in enumerate(files):
        catalog_lines.append(f"{i}: {f['name']} — {f['description']}")
    catalog = "\n".join(catalog_lines)

    prompt = (
        "Given the recent conversation and the memory catalog below, "
        "select the indices of memories that are clearly relevant. "
        "Return ONLY a JSON array of integers, e.g. [0, 3]. "
        "If none are relevant, return [].\n\n"
        f"Recent conversation:\n{recent}\n\n"
        f"Memory catalog:\n{catalog}"
    )

    try:
        response = _get_client().messages.create(
            model=_get_model(),
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )

        # 添加这几行来查看缓存命中情况
        print(response.usage,'2')
        text = extract_text(response.content).strip()
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(files):
                    selected.append(files[idx]["filename"])
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        pass

    # 降级：基于关键词匹配 name + description
    keywords = [w.lower() for w in recent.split() if len(w) > 3]
    selected = []
    for f in files:
        text = (f["name"] + " " + f["description"]).lower()
        if any(kw in text for kw in keywords):
            selected.append(f["filename"])
            if len(selected) >= max_items:
                break
    return selected


def load_memories(messages: list) -> str:
    """加载相关记忆内容，用于注入上下文。

    注入前会按「当前技能集合」过滤：仅关联已删除技能的记忆不会被注入，
    确保 AI 助手只提及技能管理里现存的技能。
    """
    selected_files = select_relevant_memories(messages)
    if not selected_files:
        return ""

    current = _current_skill_names()
    parts = ["<relevant_memories>"]
    for filename in selected_files:
        content = read_memory_file(filename)
        if not content:
            continue
        skill = _memory_skill(content)
        if skill and skill not in current:
            continue
        parts.append(content)
    if len(parts) == 1:
        return ""
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)


def delete_memories_for_skill(skill_name: str) -> int:
    """删除与某技能关联的所有记忆文件，并重建索引。

    在技能被删除时调用，保持记忆系统与技能管理一致。
    """
    if not skill_name:
        return 0
    removed = 0
    for f in list(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        if _memory_skill(raw) == skill_name:
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass
    _rebuild_index()
    return removed


def extract_memories(messages: list):
    """从最近对话中提取新记忆。每次 turn 结束后运行。"""
    dialogue_parts = []
    for msg in messages[-10:]:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(getattr(b, "text", "")) for b in content
                if getattr(b, "type", None) == "text"
            )
        if isinstance(content, str) and content.strip():
            dialogue_parts.append(f"{role}: {content}")
    dialogue = "\n".join(dialogue_parts)

    if not dialogue.strip():
        return

    # 检查已有记忆，避免重复
    existing = list_memory_files()
    existing_desc = "\n".join(f"- {m['name']}: {m['description']}" for m in existing) if existing else "(none)"

    prompt = (
        "Extract user preferences, constraints, or project facts from this dialogue.\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n"
        "- name: short kebab-case identifier (e.g. 'user-preference-tabs')\n"
        "- type: one of 'user' (user preference), 'feedback' (guidance), "
        "'project' (project fact), 'reference' (external pointer)\n"
        "- description: one-line summary for index lookup\n"
        "- body: full detail in markdown\n"
        "If nothing new or already covered by existing memories, return [].\n\n"
        f"Existing memories:\n{existing_desc}\n\n"
        f"Dialogue:\n{dialogue[:4000]}"
    )

    try:
        response = _get_client().messages.create(
            model=_get_model(), messages=[{"role": "user", "content": prompt}], max_tokens=800
        )

        # 添加这几行来查看缓存命中情况
        print(response.usage,'3')
        text = extract_text(response.content).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())
        if not items:
            return
        count = 0
        for mem in items:
            name = mem.get("name", f"memory_{int(time.time())}")
            mem_type = mem.get("type", "user")
            desc = mem.get("description", "")
            body = mem.get("body", "")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)
                count += 1
        if count:
            print(f"\n\033[33m[Memory: extracted {count} new memories]\033[0m")
    except Exception:
        pass


CONSOLIDATE_THRESHOLD = 10


def consolidate_memories():
    """合并重复/过期记忆。当文件数 ≥ 阈值时触发。"""
    files = list_memory_files()
    if len(files) < CONSOLIDATE_THRESHOLD:
        return

    catalog = "\n\n".join(
        f"## {f['filename']}\nname: {f['name']}\ndescription: {f['description']}\n{f['body']}"
        for f in files
    )

    prompt = (
        "Consolidate the following memory files. Rules:\n"
        "1. Merge duplicates into one\n"
        "2. Remove outdated/contradicted memories\n"
        "3. Keep the total under 30 memories\n"
        "4. Preserve important user preferences above all\n"
        "Return a JSON array. Each item: {name, type, description, body}.\n\n"
        f"{catalog[:16000]}"
    )

    try:
        response = _get_client().messages.create(
            model=_get_model(), messages=[{"role": "user", "content": prompt}], max_tokens=3000
        )

        # 添加这几行来查看缓存命中情况
        print(response.usage,'4')
        text = extract_text(response.content).strip()
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            return
        items = json.loads(match.group())

        # 删除旧记忆文件（保留 MEMORY.md）
        for f in MEMORY_DIR.glob("*.md"):
            if f.name != "MEMORY.md":
                f.unlink()

        for mem in items:
            name = mem.get("name", f"memory_{int(time.time())}")
            mem_type = mem.get("type", "user")
            desc = mem.get("description", "")
            body = mem.get("body", "")
            if desc and body:
                write_memory_file(name, mem_type, desc, body)

        print(f"\n\033[33m[Memory: consolidated {len(files)} → {len(items)} memories]\033[0m")
    except Exception:
        pass


def extract_text(content) -> str:
    """从 Anthropic SDK 的 content 块中提取文本"""
    if not isinstance(content, list):
        return str(content)
    return "\n".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text")


def build_system() -> str:
    """构建 system prompt，包含记忆索引"""
    index = read_memory_index()
    memories_section = f"\n\nMemories available:\n{index}" if index else ""
    return (
        f"You are a Learning Manager Agent at {WORKDIR}."
        f"{memories_section}\n"
        "Your job is to help users track their learning progress across multiple skills.\n"
        "Skills can be: IELTS, AI-Agent development, makeup, or anything else.\n"
        "When a user mentions a skill, ALWAYS use create_learning_plan to create a learning plan.\n"
        "When a user reports progress, ALWAYS use update_progress to save it.\n"
        "Use the memory system to remember what the user learned across sessions.\n"
        "Extract learning preferences and goals as memories."
    )
