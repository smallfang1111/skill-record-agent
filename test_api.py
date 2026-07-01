#!/usr/bin/env python3
"""
测试 API 接口
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_create_skill():
    """测试创建技能"""
    print("测试：创建技能")
    response = requests.post(f"{BASE_URL}/api/skills", json={
        "name": "测试技能",
        "goal": "测试目标",
        "steps": ["步骤1", "步骤2", "步骤3"]
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    return response.json().get("skill", {}).get("id")

def test_get_skills():
    """测试获取技能列表"""
    print("\n测试：获取技能列表")
    response = requests.get(f"{BASE_URL}/api/skills")
    print(f"状态码: {response.status_code}")
    print(f"技能数量: {len(response.json().get('skills', []))}")

def test_update_progress(skill_id):
    """测试更新进度"""
    print("\n测试：更新进度")
    response = requests.post(f"{BASE_URL}/api/progress", json={
        "skill_name": "测试技能",
        "completed_step": "步骤1",
        "note": "测试备注"
    })
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")

def test_delete_skill(skill_id):
    """测试删除技能"""
    print("\n测试：删除技能")
    response = requests.delete(f"{BASE_URL}/api/skills/{skill_id}")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")

if __name__ == "__main__":
    try:
        # 测试创建
        skill_id = test_create_skill()
        
        # 测试获取列表
        test_get_skills()
        
        # 测试更新进度
        if skill_id:
            test_update_progress(skill_id)
        
        # 测试删除
        if skill_id:
            test_delete_skill(skill_id)
        
        print("\n✅ 所有测试完成！")
    except requests.exceptions.ConnectionError:
        print("❌ 错误：无法连接到后端，请确保后端正在运行（python backend/main.py）")
    except Exception as e:
        print(f"❌ 错误：{e}")
