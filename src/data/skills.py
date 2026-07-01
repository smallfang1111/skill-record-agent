"""
技能数据存储模块

使用 JSON 文件存储技能数据，提供 CRUD 操作。
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# 数据文件路径
DATA_DIR = Path(__file__).parent.parent.parent / "data"
SKILLS_FILE = DATA_DIR / "skills.json"

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_skills() -> List[dict]:
    """加载所有技能"""
    if not SKILLS_FILE.exists():
        return []
    
    try:
        with open(SKILLS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_skills(skills: List[dict]):
    """保存所有技能"""
    with open(SKILLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)


def create_skill(name: str, goal: str, steps: List[str]) -> dict:
    """创建新技能"""
    skills = load_skills()
    
    # 检查是否已存在
    for skill in skills:
        if skill['name'] == name:
            raise ValueError(f"技能 '{name}' 已存在")
    
    # 创建新技能
    skill = {
        'id': datetime.now().strftime('%Y%m%d%H%M%S'),
        'name': name,
        'goal': goal,
        'steps': [
            {
                'id': f"{datetime.now().strftime('%Y%m%d%H%M%S')}-{i}",
                'content': step,
                'status': 'pending',
                'note': '',
                'completedAt': None
            }
            for i, step in enumerate(steps)
        ],
        'createdAt': datetime.now().isoformat(),
        'updatedAt': datetime.now().isoformat()
    }
    
    skills.append(skill)
    save_skills(skills)
    
    return skill


def get_skill(skill_id: str) -> Optional[dict]:
    """获取单个技能"""
    skills = load_skills()
    for skill in skills:
        if skill['id'] == skill_id:
            return skill
    return None


def update_step(skill_id: str, step_id: str, note: str = '') -> dict:
    """更新步骤状态（完成）"""
    skills = load_skills()
    
    for skill in skills:
        if skill['id'] == skill_id:
            for step in skill['steps']:
                if step['id'] == step_id:
                    step['status'] = 'completed'
                    step['note'] = note
                    step['completedAt'] = datetime.now().isoformat()
                    skill['updatedAt'] = datetime.now().isoformat()
                    save_skills(skills)
                    return skill
    
    raise ValueError(f"步骤 {step_id} 不存在")


def update_note(skill_id: str, step_id: str, note: str) -> dict:
    """仅更新步骤笔记，不改变完成状态"""
    skills = load_skills()
    
    for skill in skills:
        if skill['id'] == skill_id:
            for step in skill['steps']:
                if step['id'] == step_id:
                    step['note'] = note
                    skill['updatedAt'] = datetime.now().isoformat()
                    save_skills(skills)
                    return skill
    
    raise ValueError(f"步骤 {step_id} 不存在")


def delete_skill(skill_id: str):
    """删除技能"""
    skills = load_skills()
    skills = [s for s in skills if s['id'] != skill_id]
    save_skills(skills)


def get_timeline() -> list:
    """获取学习时间线（按日期排序的所有事件）"""
    skills = load_skills()
    events = []

    for skill in skills:
        created_at = skill.get('createdAt') or ''
        updated_at = skill.get('updatedAt') or ''

        # 创建事件
        if created_at and len(created_at) >= 10:
            events.append({
                'date': created_at[:10],
                'time': created_at,
                'type': 'create',
                'skill_name': skill.get('name', ''),
                'skill_id': skill.get('id', ''),
                'content': f'创建了技能「{skill.get("name", "")}」'
            })

        # 步骤完成事件
        for step in skill.get('steps', []):
            if step.get('status') == 'completed':
                comp_at = step.get('completedAt') or ''
                if comp_at and len(comp_at) >= 10:
                    events.append({
                        'date': comp_at[:10],
                        'time': comp_at,
                        'type': 'complete',
                        'skill_name': skill.get('name', ''),
                        'skill_id': skill.get('id', ''),
                        'step_content': step.get('content', ''),
                        'note': step.get('note') or '',
                        'content': f'完成了「{skill.get("name", "")}」的步骤：{step.get("content", "")}'
                    })

        # 更新事件（排除与创建时间相同的）
        if updated_at and updated_at != created_at and len(updated_at) >= 10:
            events.append({
                'date': updated_at[:10],
                'time': updated_at,
                'type': 'update',
                'skill_name': skill.get('name', ''),
                'skill_id': skill.get('id', ''),
                'content': f'更新了技能「{skill.get("name", "")}」'
            })

    # 按时间倒序排序
    events.sort(key=lambda x: x.get('time', ''), reverse=True)
    return events
