#!/usr/bin/env python3
"""
学习管家 - Streamlit Web 界面
=============================
将 learning_agent.py 的能力封装成美观的 Web 应用。
支持：多技能管理、学习计划创建、进度追踪、记忆系统可视化。
"""

import os, json, time, re, subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

import streamlit as st

from anthropic import Anthropic
from dotenv import load_dotenv

# ── 配置 ─────────────────────────────────────────────────
load_dotenv(override=True)

WORKDIR = Path.cwd()
MEMORY_DIR = WORKDIR / "data" / "memory"
SKILLS_DIR = WORKDIR / "skills"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
SKILLS_DIR.mkdir(exist_ok=True)

# 导入 agent 模块
import sys
sys.path.insert(0, str(WORKDIR))

from src.agent.memory import (
    _parse_frontmatter,
    list_memory_files,
    write_memory_file,
    _rebuild_index
)
from src.agent.tools import extract_text

# 使用 Streamlit 缓存 LLM 客户端，避免重复创建
@st.cache_resource
def get_llm_client():
    return Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))

@st.cache_resource
def get_model_id():
    return os.environ.get("MODEL_ID", "deepseek-chat")

client = get_llm_client()
MODEL = get_model_id()

# ── 页面配置 ─────────────────────────────────────────────

st.set_page_config(
    page_title="📚 学习管家",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 样式 ─────────────────────────────────────────────────

st.markdown("""
<style>
    /* 主标题 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.2rem;
    }
    .main-subtitle {
        font-size: 1rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }

    /* 技能卡片 */
    .skill-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    .skill-card:hover {
        transform: translateY(-2px);
    }
    .skill-card h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.3rem;
    }
    .skill-card .progress-text {
        font-size: 0.9rem;
        opacity: 0.9;
    }

    /* 进度条 */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2);
    }

    /* 步骤列表 */
    .step-item {
        display: flex;
        align-items: center;
        padding: 0.6rem 1rem;
        background: #F9FAFB;
        border-radius: 10px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #E5E7EB;
        transition: all 0.2s;
    }
    .step-item.completed {
        border-left-color: #10B981;
        background: #F0FDF4;
    }
    .step-item.pending {
        border-left-color: #F59E0B;
    }
    .step-item .step-number {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background: #E5E7EB;
        color: #374151;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 1rem;
        flex-shrink: 0;
    }
    .step-item.completed .step-number {
        background: #10B981;
        color: white;
    }

    /* 聊天消息 */
    .chat-message {
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 0.8rem;
        max-width: 85%;
    }
    .chat-message.user {
        background: #EFF6FF;
        border: 1px solid #BFDBFE;
        margin-left: auto;
    }
    .chat-message.assistant {
        background: #F3F4F6;
        border: 1px solid #E5E7EB;
    }

    /* 侧边栏 */
    .sidebar-section {
        margin-bottom: 1.5rem;
    }
    .sidebar-section h3 {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #9CA3AF;
        margin-bottom: 0.8rem;
    }

    /* 标签页 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 0.5rem 1.2rem;
        border-radius: 8px 8px 0 0;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  记忆系统
# ═══════════════════════════════════════════════════════════

def _parse_frontmatter(text: str) -> tuple[dict, str]:
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


def list_memory_files() -> list[dict]:
    """列出所有记忆文件"""
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
            "body": body.strip(),
        })
    return result


def write_memory_file(name: str, mem_type: str, description: str, body: str):
    """写入一个记忆文件"""
    slug = name.lower().replace(" ", "-").replace("/", "-")
    filename = f"{slug}.md"
    filepath = MEMORY_DIR / filename
    filepath.write_text(
        f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n\n{body}\n",
        encoding='utf-8'
    )
    _rebuild_index()
    return filepath


def _rebuild_index():
    """重建 MEMORY.md 索引"""
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
        (MEMORY_DIR / "MEMORY.md").write_text("\n".join(lines) + "\n" if lines else "", encoding='utf-8')
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════
#  技能 & 进度存储（用文件持久化）
# ═══════════════════════════════════════════════════════════

SKILLS_FILE = WORKDIR / ".skills_data.json"

def load_skills_data() -> dict:
    """加载技能数据"""
    if SKILLS_FILE.exists():
        try:
            return json.loads(SKILLS_FILE.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {"skills": {}}

def save_skills_data(data: dict):
    """保存技能数据"""
    SKILLS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def get_skill(name: str) -> dict:
    """获取单个技能数据"""
    data = load_skills_data()
    return data["skills"].get(name, {"steps": [], "progress": [], "goal": ""})

def update_skill(name: str, goal: str, steps: list):
    """更新/创建技能"""
    data = load_skills_data()
    if name not in data["skills"]:
        data["skills"][name] = {"steps": [], "progress": [], "goal": "", "created_at": datetime.now().isoformat()}
    data["skills"][name]["goal"] = goal
    # 合并新步骤（不覆盖已有的）
    existing_steps = data["skills"][name]["steps"]
    for step in steps:
        if step not in [s["content"] for s in existing_steps]:
            existing_steps.append({"content": step, "status": "pending"})
    data["skills"][name]["steps"] = existing_steps
    save_skills_data(data)

def add_progress(skill_name: str, completed: str, note: str = ""):
    """添加进度记录"""
    data = load_skills_data()
    if skill_name not in data["skills"]:
        data["skills"][skill_name] = {"steps": [], "progress": [], "goal": ""}
    
    # 标记对应步骤为已完成
    for step in data["skills"][skill_name]["steps"]:
        if step["content"] == completed:
            step["status"] = "completed"
            break
    
    data["skills"][skill_name]["progress"].append({
        "completed": completed,
        "note": note,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save_skills_data(data)

def get_skill_progress(skill_name: str) -> tuple:
    """获取技能进度 (已完成数, 总步骤数, 百分比)"""
    skill = get_skill(skill_name)
    steps = skill.get("steps", [])
    if not steps:
        return 0, 0, 0
    completed = sum(1 for s in steps if s["status"] == "completed")
    return completed, len(steps), int(completed / len(steps) * 100)


# ═══════════════════════════════════════════════════════════
#  LLM 智能助手
# ═══════════════════════════════════════════════════════════

def load_memory_context() -> str:
    """加载记忆上下文"""
    files = list_memory_files()
    if not files:
        return ""
    parts = ["<relevant_memories>"]
    for f in files:
        parts.append(
            f"---\nname: {f['name']}\ndescription: {f['description']}\ntype: {f['type']}\n---\n\n{f['body']}"
        )
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)


@st.cache_data(ttl=300)  # 缓存 5 分钟，避免重复读取
def get_system_prompt() -> str:
    """构建系统提示词（带缓存）"""
    index = ""
    idx_file = MEMORY_DIR / "MEMORY.md"
    if idx_file.exists():
        index = idx_file.read_text(encoding='utf-8').strip()
    
    memory_section = f"\n\nMemories available:\n{index}" if index else ""
    
    return (
        f"You are a Learning Manager Agent at {WORKDIR}."
        f"{memory_section}\n"
        "Your job is to help users track their learning progress across multiple skills.\n"
        "Skills can be: IELTS, AI-Agent development, makeup, or anything else.\n"
        "When a user mentions a new skill, create a learning plan for it.\n"
        "When a user reports progress, record it.\n"
        "Use the memory system to remember what the user learned across sessions.\n"
        "Extract learning preferences and goals as memories.\n\n"
        "IMPORTANT: You live inside a Streamlit web app. The app handles learning plans "
        "and progress tracking itself. Your job is to:\n"
        "1. Detect skills mentioned by the user\n"
        "2. Guide the user to create learning plans\n"
        "3. Ask the user what specific steps they want to include\n"
        "4. Confirm progress updates\n"
        "5. Provide encouragement and study tips\n\n"
        "Be friendly, encouraging, and use emojis occasionally. "
        "You are a warm and supportive learning companion! 🎯"
    )


def chat_with_llm(messages: list) -> str:
    """与 LLM 对话"""
    try:
        system = get_system_prompt()
        response = client.messages.create(
            model=MODEL,
            system=system,
            messages=messages,
            max_tokens=2000,
        )
        
        # 打印 token 使用情况（用于调试）
        if hasattr(response, 'usage'):
            print(f"[Token 使用] 输入: {response.usage.input_tokens}, 输出: {response.usage.output_tokens}")
            if hasattr(response.usage, 'cache_creation_input_tokens'):
                print(f"[缓存] 创建: {response.usage.cache_creation_input_tokens}, 命中: {response.usage.cache_read_input_tokens}")
        
        text = ""
        for block in response.content:
            if hasattr(block, 'type') and block.type == 'text':
                text += block.text
            elif isinstance(block, dict) and block.get('type') == 'text':
                text += block.get('text', '')
        return text
    except Exception as e:
        return f"🤖 (AI暂时不在线，错误: {str(e)[:100]})"


# ═══════════════════════════════════════════════════════════
#  Streamlit 页面
# ═══════════════════════════════════════════════════════════

def init_session_state():
    """初始化 session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"
    if "editing_skill" not in st.session_state:
        st.session_state.editing_skill = None


def main():
    init_session_state()
    
    # ── 侧边栏 ─────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.5rem;">
            <div style="font-size: 3rem;">📚</div>
            <div style="font-size: 1.2rem; font-weight: 600; color: #1E3A5F;">学习管家</div>
            <div style="font-size: 0.8rem; color: #9CA3AF;">你的专属学习伴侣</div>
        </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # 导航
        st.markdown('<div class="sidebar-section"><h3>导航</h3></div>', unsafe_allow_html=True)
        
        if st.button("🏠 仪表盘", use_container_width=True, 
                      type="primary" if st.session_state.current_page == "dashboard" else "secondary"):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        if st.button("📋 技能管理", use_container_width=True,
                      type="primary" if st.session_state.current_page == "skills" else "secondary"):
            st.session_state.current_page = "skills"
            st.rerun()
        
        if st.button("💬 AI 学习助手", use_container_width=True,
                      type="primary" if st.session_state.current_page == "chat" else "secondary"):
            st.session_state.current_page = "chat"
            st.rerun()
        
        if st.button("🧠 记忆库", use_container_width=True,
                      type="primary" if st.session_state.current_page == "memories" else "secondary"):
            st.session_state.current_page = "memories"
            st.rerun()
        
        st.divider()
        
        # 快速技能概览
        st.markdown('<div class="sidebar-section"><h3>我的技能</h3></div>', unsafe_allow_html=True)
        data = load_skills_data()
        if data["skills"]:
            for name in sorted(data["skills"].keys()):
                completed, total, pct = get_skill_progress(name)
                st.markdown(f"""
                <div style="padding: 0.4rem 0; border-bottom: 1px solid #F3F4F6;">
                    <div style="display: flex; justify-content: space-between; font-size: 0.9rem;">
                        <span>{name}</span>
                        <span style="color: #6B7280;">{completed}/{total}</span>
                    </div>
                    <div style="height: 4px; background: #E5E7EB; border-radius: 2px; margin-top: 4px;">
                        <div style="height: 100%; width: {pct}%; background: linear-gradient(90deg, #667eea, #764ba2); border-radius: 2px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.caption("还没有技能，快去添加吧！")
    
    # ── 主区域 ─────────────────────────────────────────
    
    if st.session_state.current_page == "dashboard":
        render_dashboard()
    elif st.session_state.current_page == "skills":
        render_skills()
    elif st.session_state.current_page == "chat":
        render_chat()
    elif st.session_state.current_page == "memories":
        render_memories()


# ═══════════════════════════════════════════════════════════
#  仪表盘页面
# ═══════════════════════════════════════════════════════════

def render_dashboard():
    st.markdown('<div class="main-title">🏠 学习仪表盘</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">一览你的所有学习进度</div>', unsafe_allow_html=True)
    
    data = load_skills_data()
    
    if not data["skills"]:
        # 空状态
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style="text-align: center; padding: 4rem 0;">
                <div style="font-size: 5rem; margin-bottom: 1rem;">🎯</div>
                <h3>开始你的学习之旅</h3>
                <p style="color: #6B7280;">
                    在「技能管理」中添加技能和学习计划，<br>
                    或直接与 AI 助手聊天来创建计划！
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            col_a, col_b, col_c = st.columns(3)
            with col_b:
                if st.button("📋 去添加技能", use_container_width=True):
                    st.session_state.current_page = "skills"
                    st.rerun()
        return
    
    # ── 统计概览 ──
    total_skills = len(data["skills"])
    total_steps = sum(len(s["steps"]) for s in data["skills"].values())
    total_completed = sum(
        sum(1 for step in s["steps"] if step["status"] == "completed")
        for s in data["skills"].values()
    )
    total_progress = int(total_completed / total_steps * 100) if total_steps > 0 else 0
    
    cols = st.columns(4)
    metrics = [
        ("📚 技能数", total_skills, ""),
        ("📋 总任务", total_steps, ""),
        ("✅ 已完成", total_completed, f"{total_progress}%"),
        ("🔥 完成率", f"{total_progress}%", f"{total_completed}/{total_steps}"),
    ]
    for col, (label, value, delta) in zip(cols, metrics):
        with col:
            st.metric(label, value, delta)
    
    st.divider()
    
    # ── 技能卡片 ──
    st.subheader("📊 各技能进度")
    skill_cols = st.columns(2)
    for i, (name, info) in enumerate(sorted(data["skills"].items())):
        with skill_cols[i % 2]:
            completed, total, pct = get_skill_progress(name)
            goal = info.get("goal", "未设置目标")
            
            st.markdown(f"""
            <div class="skill-card">
                <h3>{'🎓' if 'ielts' in name.lower() or '雅思' in name else '🤖' if 'ai' in name.lower() or 'agent' in name.lower() else '📖'} {name}</h3>
                <div class="progress-text">🎯 {goal}</div>
                <div class="progress-text">进展: {completed}/{total} 步 ({pct}%)</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.progress(pct / 100)
            
            # 显示最近进度
            progress_list = info.get("progress", [])
            if progress_list:
                last = progress_list[-1]
                st.caption(f"🕐 最近: {last['completed']} ({last['time']})")
            
            if st.button(f"📝 查看详情", key=f"view_{name}"):
                st.session_state.editing_skill = name
                st.session_state.current_page = "skills"
                st.rerun()
            
            st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  技能管理页面
# ═══════════════════════════════════════════════════════════

def render_skills():
    st.markdown('<div class="main-title">📋 技能管理</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">管理你的学习技能、创建计划和记录进度</div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["➕ 添加技能", "📂 已有技能"])
    
    # ── Tab 1: 添加技能 ──
    with tab1:
        st.markdown("### 创建新的学习计划")
        
        with st.form("new_skill_form"):
            col1, col2 = st.columns(2)
            with col1:
                skill_name = st.text_input("📌 技能名称", placeholder="例如：雅思、AI-Agent开发、化妆")
            with col2:
                skill_goal = st.text_input("🎯 学习目标", placeholder="例如：考到7分、搭建第一个Agent")
            
            st.markdown("**📝 学习步骤**（每行一个步骤）")
            steps_text = st.text_area(
                "输入步骤",
                placeholder="听力精听训练\n阅读长难句分析\n口语模考练习\n写作大作文训练",
                height=150,
            )
            
            submitted = st.form_submit_button("🚀 创建学习计划", use_container_width=True)
            
            if submitted and skill_name:
                steps = [s.strip() for s in steps_text.split("\n") if s.strip()]
                if steps:
                    update_skill(skill_name, skill_goal, steps)
                    
                    # 也写入记忆系统
                    write_memory_file(
                        f"skill-{skill_name}",
                        "project",
                        f"{skill_name} 学习计划",
                        f"## {skill_name} 学习计划\n- 目标：{skill_goal}\n- 步骤数：{len(steps)}\n- 创建时间：{datetime.now().strftime('%Y-%m-%d')}"
                    )
                    
                    st.success(f"✅ 已为「{skill_name}」创建学习计划，共 {len(steps)} 个步骤！")
                    st.balloons()
                else:
                    st.error("请至少输入一个步骤！")
            elif submitted and not skill_name:
                st.error("请输入技能名称！")
    
    # ── Tab 2: 已有技能 ──
    with tab2:
        data = load_skills_data()
        if not data["skills"]:
            st.info("还没有添加任何技能，去「添加技能」标签页创建一个吧！")
            return
        
        # 显示所有技能
        for name, info in sorted(data["skills"].items()):
            with st.expander(f"📖 {name}", expanded=(st.session_state.editing_skill == name)):
                completed, total, pct = get_skill_progress(name)
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**目标：** {info.get('goal', '未设置')}")
                    st.markdown(f"**进度：** {completed}/{total} 步完成")
                with col2:
                    st.metric("完成率", f"{pct}%")
                
                st.progress(pct / 100)
                
                # 步骤列表
                st.markdown("#### 📋 学习步骤")
                for i, step in enumerate(info["steps"]):
                    status = step["status"]
                    icon = "✅" if status == "completed" else "⏳"
                    st.markdown(f"""
                    <div class="step-item {'completed' if status == 'completed' else 'pending'}">
                        <span class="step-number">{i + 1}</span>
                        <span style="flex: 1;">{step['content']}</span>
                        <span>{icon}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                # 记录进度
                st.markdown("#### ✍️ 记录进度")
                
                # 找出未完成的步骤
                pending_steps = [s for s in info["steps"] if s["status"] != "completed"]
                
                if pending_steps:
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        completed_step = st.selectbox(
                            "选择刚完成的步骤",
                            [s["content"] for s in pending_steps],
                            key=f"select_{name}"
                        )
                    with col_b:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("✅ 标记完成", key=f"done_{name}"):
                            add_progress(name, completed_step)
                            # 也写入记忆
                            write_memory_file(
                                f"progress-{name}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                "user",
                                f"{name} 学习进度",
                                f"完成：{completed_step}\n时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}"
                            )
                            st.success(f"✅ 「{completed_step}」已标记完成！")
                            st.rerun()
                else:
                    st.success("🎉 所有步骤已完成！太棒了！")
                
                # 进度历史
                progress_list = info.get("progress", [])
                if progress_list:
                    st.markdown("#### 📜 进度历史")
                    for entry in reversed(progress_list[-10:]):
                        note_text = f" — {entry['note']}" if entry.get('note') else ""
                        st.caption(f"✅ {entry['completed']}{note_text}  🕐 {entry['time']}")


# ═══════════════════════════════════════════════════════════
#  AI 聊天页面
# ═══════════════════════════════════════════════════════════

def render_chat():
    st.markdown('<div class="main-title">💬 AI 学习助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">和 AI 聊天，让它帮你制定学习计划、记录进度</div>', unsafe_allow_html=True)
    
    # 快捷操作
    quick_cols = st.columns(4)
    quick_prompts = [
        ("🎯 帮我制定雅思计划", "帮我制定一个雅思7分的学习计划"),
        ("🤖 我想学AI Agent", "我想学习AI Agent开发，帮我规划一下"),
        ("💄 学化妆", "我是化妆新手，帮我制定一个学习化妆的计划"),
        ("📝 记录进度", "我今天完成了听力训练"),
    ]
    
    for col, (label, prompt) in zip(quick_cols, quick_prompts):
        with col:
            if st.button(label, use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": prompt})
                # 获取AI回复
                with st.spinner("AI正在思考..."):
                    reply = chat_with_llm(st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": reply})
                st.rerun()
    
    st.divider()
    
    # 聊天记录
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.messages:
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                st.markdown(f"""
                <div class="chat-message user">
                    <div style="font-weight: 600; margin-bottom: 0.3rem; color: #1E40AF;">🧑 你</div>
                    <div>{content}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="chat-message assistant">
                    <div style="font-weight: 600; margin-bottom: 0.3rem; color: #6B7280;">🤖 AI 助手</div>
                    <div>{content}</div>
                </div>
                """, unsafe_allow_html=True)
    
    # 输入框
    st.divider()
    
    col_input, col_send = st.columns([5, 1])
    with col_input:
        user_input = st.text_input(
            "输入你的问题...",
            placeholder="例如：帮我制定一个学习计划 / 我今天完成了...",
            label_visibility="collapsed",
            key="chat_input",
        )
    with col_send:
        st.markdown("<br>", unsafe_allow_html=True)
        send_clicked = st.button("📤 发送", use_container_width=True)
    
    if send_clicked and user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.spinner("🤖 AI正在思考..."):
            reply = chat_with_llm(st.session_state.messages)
        
        st.session_state.messages.append({"role": "assistant", "content": reply})
        st.rerun()


# ═══════════════════════════════════════════════════════════
#  记忆库页面
# ═══════════════════════════════════════════════════════════

def render_memories():
    st.markdown('<div class="main-title">🧠 记忆库</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-subtitle">AI 记住的关于你的学习偏好和进度</div>', unsafe_allow_html=True)
    
    memories = list_memory_files()
    
    if not memories:
        st.info("还没有任何记忆。和 AI 助手聊聊天，它会自动记住你的偏好和进度！")
        return
    
    # 按类型分类
    mem_types = {"user": "👤 用户偏好", "feedback": "💬 反馈", "project": "📁 项目", "reference": "🔗 参考"}
    
    for mem_type, type_label in mem_types.items():
        type_mems = [m for m in memories if m["type"] == mem_type]
        if type_mems:
            st.markdown(f"### {type_label} ({len(type_mems)})")
            for mem in type_mems:
                with st.expander(f"📄 {mem['name']}"):
                    st.caption(f"*{mem['description']}*")
                    st.markdown(mem["body"])
            st.divider()
    
    # 管理按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🗑️ 清除所有记忆", type="secondary"):
            for f in MEMORY_DIR.glob("*.md"):
                if f.name != "MEMORY.md":
                    f.unlink()
            _rebuild_index()
            st.success("记忆已清除！")
            st.rerun()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("学习管家 Web UI 启动中...")
    print("=" * 60)
    print("访问地址: http://localhost:8501")
    print("=" * 60 + "\n")
    main()
