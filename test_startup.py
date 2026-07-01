#!/usr/bin/env python3
"""
测试 web.py 的启动时间，找出卡住的原因
"""

import time
import sys
from pathlib import Path

# 设置 stdout 编码为 utf-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("=" * 60)
print("开始测试启动时间...")
print("=" * 60)

# 测试 1: 基本导入
print("\n[1/6] 导入基本模块...")
start = time.time()
import os
import json
from dotenv import load_dotenv
print(f"    [OK] 完成 ({time.time() - start:.2f}s)")

# 测试 2: 导入 anthropic
print("\n[2/6] 导入 anthropic...")
start = time.time()
from anthropic import Anthropic
print(f"    [OK] 完成 ({time.time() - start:.2f}s)")

# 测试 3: 加载环境变量
print("\n[3/6] 加载环境变量...")
start = time.time()
load_dotenv(override=True)
base_url = os.getenv("ANTHROPIC_BASE_URL")
model = os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")
print(f"    [OK] 完成 ({time.time() - start:.2f}s)")
print(f"    ANTHROPIC_BASE_URL: {base_url}")
print(f"    MODEL_ID: {model}")

# 测试 4: 创建 LLM 客户端
print("\n[4/6] 创建 LLM 客户端...")
start = time.time()
try:
    client = Anthropic(base_url=base_url)
    print(f"    [OK] 完成 ({time.time() - start:.2f}s)")
except Exception as e:
    print(f"    [FAIL] 失败: {e}")

# 测试 5: 测试简单 API 调用
print("\n[5/6] 测试 API 连接（使用最快的模型）...")
start = time.time()
try:
    # 使用一个小的测试请求
    response = client.messages.create(
        model=model,
        max_tokens=10,
        messages=[{"role": "user", "content": "hi"}]
    )
    elapsed = time.time() - start
    print(f"    [OK] API 响应成功 ({elapsed:.2f}s)")
    print(f"    响应内容: {response.content[0].text[:50]}")
except Exception as e:
    elapsed = time.time() - start
    print(f"    [FAIL] API 调用失败 ({elapsed:.2f}s)")
    print(f"    错误: {e}")

# 测试 6: 导入 src.agent.memory
print("\n[6/6] 导入 src.agent.memory...")
start = time.time()
try:
    sys.path.insert(0, str(Path(__file__).parent))
    from src.agent import memory as mem
    print(f"    [OK] 完成 ({time.time() - start:.2f}s)")
except Exception as e:
    print(f"    [FAIL] 失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
