"""
会话管理模块

类似 DeepSeek 的多会话系统：
- 每个会话有独立的 ID、标题、消息列表
- 会话按时间分组显示（Today, Yesterday, 7 Days, 30 Days+）
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Dict

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SETTINGS_FILE = DATA_DIR / "settings.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_sessions_file() -> Path:
    """根据设置中的工作区目录决定会话存储位置；未配置则回退到默认 DATA_DIR"""
    workspace = ""
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
            workspace = (data.get('workspace') or '').strip()
        except Exception:
            pass
    if workspace:
        target = Path(workspace)
    else:
        target = DATA_DIR
    target.mkdir(parents=True, exist_ok=True)
    return target / "chat_sessions.json"


def load_sessions() -> List[dict]:
    """加载所有会话"""
    sessions_file = _resolve_sessions_file()
    if not sessions_file.exists():
        return []
    try:
        with open(sessions_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_sessions(sessions: List[dict]):
    """保存所有会话"""
    sessions_file = _resolve_sessions_file()
    sessions_file.parent.mkdir(parents=True, exist_ok=True)
    with open(sessions_file, 'w', encoding='utf-8') as f:
        json.dump(sessions, f, ensure_ascii=False, indent=2)


def create_session(title: str = "新对话") -> dict:
    """创建新会话"""
    sessions = load_sessions()
    
    session = {
        'id': datetime.now().strftime('%Y%m%d%H%M%S%f'),
        'title': title,
        'messages': [],
        'createdAt': datetime.now().isoformat(),
        'updatedAt': datetime.now().isoformat()
    }
    
    # 新会话插入到最前面
    sessions.insert(0, session)
    save_sessions(sessions)
    
    return session


def get_session(session_id: str) -> Optional[dict]:
    """获取单个会话"""
    for s in load_sessions():
        if s['id'] == session_id:
            return s
    return None


def add_message_to_session(session_id: str, role: str, content: str):
    """给指定会话添加消息，返回更新后的会话"""
    sessions = load_sessions()
    
    for s in sessions:
        if s['id'] == session_id:
            msg = {
                'role': role,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }
            s['messages'].append(msg)
            s['updatedAt'] = datetime.now().isoformat()

            # 如果是第一条用户消息，用它作为会话标题（截断）
            if role == 'user' and len(s['messages']) == 1:
                s['title'] = content[:30] + ('...' if len(content) > 30 else '')

            save_sessions(sessions)
            return s
    
    raise ValueError(f"会话 {session_id} 不存在")


def delete_session(session_id: str):
    """删除会话"""
    sessions = [s for s in load_sessions() if s['id'] != session_id]
    save_sessions(sessions)


def get_grouped_sessions() -> Dict[str, List[dict]]:
    """获取按时间分组的会话列表（用于左侧栏）"""
    sessions = load_sessions()
    now = datetime.now()
    
    today = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    seven_days_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')
    
    groups: Dict[str, List[dict]] = {
        'Today': [],
        'Yesterday': [],
        'Previous 7 Days': [],
        'Older': []
    }

    for s in sessions:
        updated_at = s.get('updatedAt', s.get('createdAt', ''))
        date_str = updated_at[:10] if len(updated_at) >= 10 else ''
        
        if date_str == today:
            groups['Today'].append(s)
        elif date_str == yesterday:
            groups['Yesterday'].append(s)
        elif date_str >= seven_days_ago:
            groups['Previous 7 Days'].append(s)
        else:
            groups['Older'].append(s)

    return groups
