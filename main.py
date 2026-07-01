#!/usr/bin/env python3
"""
Learning Manager Agent - 主入口

用法：
  python main.py                              # 交互模式
  python main.py "帮我制定一个雅思学习计划"    # 单次查询
  python main.py -q "今天学了听力"             # 单次查询（带进度更新）
  python main.py --history                     # 显示记忆索引
  python main.py --memories                    # 列出所有记忆文件
"""

import sys
from pathlib import Path

# 将项目根目录添加到 sys.path，确保可以导入 src 包
sys.path.insert(0, str(Path(__file__).parent))

# 导入并运行 CLI 入口
from src.ui.cli import main

if __name__ == "__main__":
    main()
