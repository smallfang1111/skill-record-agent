"""
对话历史存储模块

使用 JSON 文件存储对话历史，提供读写操作。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 数据文件路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
HISTORY_FILE = DATA_DIR / "chat_history.json"

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_history() -> List[dict]:
    """加载所有对话历史"""
    if not HISTORY_FILE.exists():
        return []
    
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: List[dict]):
    """保存对话历史"""
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def add_message(role: str, content: str):
    """添加一条消息到历史记录"""
    history = load_history()
    
    message = {
        'id': datetime.now().strftime('%Y%m%d%H%M%S'),
        'role': role,
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    
    history.append(message)
    save_history(history)
    
    return message


def clear_history():
    """清空历史记录"""
    save_history([])
