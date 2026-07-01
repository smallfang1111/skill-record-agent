#!/usr/bin/env python3
"""
测试 web.py 的启动时间，找出卡住的原因
"""

import time
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("开始测试 web.py 启动时间...")
print("=" * 60)

# 测试 1: 导入 streamlit
print("\n[1/5] 导入 streamlit...")
start = time.time()
import streamlit as st
print(f"    ✓ 完成 ({time.time() - start:.2f}s)")

# 测试 2: 导入 anthropic
print("\n[2/5] 导入 anthropic...")
start = time.time()
from anthropic import Anthropic
print(f"    ✓ 完成 ({time.time() - start:.2f}s)")

# 测试 3: 创建 LLM 客户端
print("\n[3/5] 创建 LLM 客户端...")
start = time.time()
from dotenv import load_dotenv
load_dotenv(override=True)

base_url = "https://api.anthropic.com"  # 使用官方 API 测试
client = Anthropic(base_url=base_url)
print(f"    ✓ 完成 ({time.time() - start:.2f}s)")

# 测试 4: 测试 API 连接
print("\n[4/5] 测试 API 连接（发送一个简单的请求）...")
start = time.time()
try:
    response = client.messages.create(
        model="claude-3-haiku-20240307",  # 使用最快的模型测试
        max_tokens=10,
        messages=[{"role": "user", "content": "Say hello"}]
    )
    print(f"    ✓ API 响应成功 ({time.time() - start:.2f}s)")
    print(f"    响应: {response.content[0].text}")
except Exception as e:
    print(f"    ✗ API 调用失败: {e}")
    print(f"    耗时: {time.time() - start:.2f}s")

# 测试 5: 导入 web.py 模块
print("\n[5/5] 导入 web.py 模块...")
start = time.time()
try:
    # 不实际运行 streamlit，只导入模块
    import importlib.util
    spec = importlib.util.spec_from_file_location("web", "src/ui/web.py")
    print(f"    ✓ 模块加载完成 ({time.time() - start:.2f}s)")
except Exception as e:
    print(f"    ✗ 模块导入失败: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
