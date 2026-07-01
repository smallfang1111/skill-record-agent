"""
终端入口模块

提供两种使用模式：
  1. 交互模式（默认） — 带彩色输出的 REPL 循环
  2. 单次查询模式 — 通过命令行参数传入问题，打印回答后退出

用法：
  python -m src.ui.cli                              # 交互模式
  python -m src.ui.cli "帮我制定一个雅思学习计划"    # 单次查询
  python -m src.ui.cli --history                    # 显示记忆索引
  python -m src.ui.cli --memories                   # 列出所有记忆文件
"""

import os
import sys
import argparse
import shutil
from pathlib import Path

# 修复 Windows 终端的编码问题
if sys.platform == "win32":
    # 设置控制台代码页为 UTF-8
    os.system("chcp 65001 > nul")
    # 重新配置 stdout/stderr 为 UTF-8
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# 导入 agent 模块
from src.agent.core import agent_loop
from src.agent.memory import (
    list_memory_files,
    read_memory_index,
    read_memory_file,
    MEMORY_DIR,
    WORKDIR
)


# ═══════════════════════════════════════════════
# 颜色常量（兼容不支持颜色的终端）
# ═══════════════════════════════════════════════

_COLORS = {
    "cyan": "\033[36m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "reset": "\033[0m",
}

# 检测终端是否支持颜色
def _supports_color() -> bool:
    return shutil.get_terminal_size().columns > 0 and sys.stdout.isatty()

if not _supports_color():
    for k in _COLORS:
        _COLORS[k] = ""

def c(name: str, text: str) -> str:
    """给文本套上颜色，并处理编码问题"""
    try:
        # 尝试编码到终端编码，如果失败则移除 emoji
        text.encode(sys.stdout.encoding or "utf-8")
        return f"{_COLORS.get(name, '')}{text}{_COLORS['reset']}"
    except UnicodeEncodeError:
        # 移除无法编码的字符（如 emoji）
        safe_text = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8")
        return f"{_COLORS.get(name, '')}{safe_text}{_COLORS['reset']}"


# ═══════════════════════════════════════════════
# Banner / 欢迎信息
# ═══════════════════════════════════════════════

BANNER = f"""
{c('bold', '╔══════════════════════════════════════════════╗')}
{c('bold', '║')}   {c('cyan', '[LM] Learning Manager Agent')}       {c('bold', '║')}
{c('bold', '║')}   {c('dim', '终端调试入口 v1.0')}                 {c('bold', '║')}
{c('bold', '╚══════════════════════════════════════════════╝')}
{c('dim', '输入问题，回车发送。输入')} {c('yellow', 'q')} {c('dim', '或')} {c('yellow', 'exit')} {c('dim', '退出。')}
"""

HELP_TEXT = f"""
{c('bold', '可用命令:')}
  {c('yellow', 'q / exit')}       退出程序
  {c('yellow', '?help')}          显示此帮助
  {c('yellow', '?history')}       查看记忆索引
  {c('yellow', '?memories')}      列出所有记忆文件
  {c('yellow', '?read <文件名>')}  读取某个记忆文件的内容
  {c('yellow', '?clear')}         清屏
  {c('yellow', '?stats')}         显示统计信息
"""


# ═══════════════════════════════════════════════
# 辅助命令处理
# ═══════════════════════════════════════════════

def cmd_history():
    """显示记忆索引"""
    index = read_memory_index()
    if index:
        print(c("green", "\n[记忆索引]"))
        print(index)
    else:
        print(c("yellow", "\n[提示] 暂无记忆。"))


def cmd_memories():
    """列出所有记忆文件"""
    files = list_memory_files()
    if not files:
        print(c("yellow", "\n[提示] 暂无记忆文件。"))
        return
    print(c("green", f"\n[共 {len(files)} 个记忆文件]"))
    for f in files:
        print(f"  {c('cyan', f['filename']):40s} {c('dim', f['description'][:60])}")


def cmd_read(filename: str):
    """读取某个记忆文件"""
    content = read_memory_file(filename)
    if content is None:
        print(c("red", f"\n[错误] 未找到记忆文件: {filename}"))
        return
    print(c("green", f"\n[{filename}]:"))
    print(content)


def cmd_stats():
    """显示统计信息"""
    memory_files = list_memory_files()
    print(c("green", "\n[统计信息]"))
    print(f"  工作目录: {c('cyan', str(WORKDIR))}")
    print(f"  记忆文件数: {c('cyan', str(len(memory_files)))}")
    print(f"  内存目录: {c('cyan', str(MEMORY_DIR))}")


def clear_screen():
    """清屏"""
    import os as _os
    _os.system('cls' if _os.name == 'nt' else 'clear')


# ═══════════════════════════════════════════════
# 交互模式
# ═══════════════════════════════════════════════

def interactive_mode():
    """进入交互式 REPL 循环"""
    print(BANNER)

    history = []
    while True:
        try:
            query = input(c("cyan", "\nlm> "))
        except (EOFError, KeyboardInterrupt):
            print(c("yellow", "\n\n[退出] 再见！"))
            break

        raw = query.strip()
        if not raw:
            continue

        # 处理退出
        if raw.lower() in ("q", "quit", "exit"):
            print(c("green", "[退出] 再见！"))
            break

        # 处理内部命令
        if raw.startswith("?"):
            cmd = raw[1:].strip().lower()
            if cmd in ("help", "h"):
                print(HELP_TEXT)
            elif cmd in ("history", "index"):
                cmd_history()
            elif cmd in ("memories", "memory", "ls"):
                cmd_memories()
            elif cmd.startswith("read "):
                filename = cmd[5:].strip()
                cmd_read(filename)
            elif cmd == "clear":
                clear_screen()
                print(BANNER)
            elif cmd == "stats":
                cmd_stats()
            else:
                print(c("yellow", f"未知命令: {raw} - 输入 ?help 查看可用命令"))
            continue

        # 正常对话
        history.append({"role": "user", "content": raw})
        try:
            agent_loop(history)
            # 打印最终回答
            last_msg = history[-1] if history else None
            if last_msg:
                content = last_msg.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if getattr(block, "type", None) == "text":
                            text = block.text
                            if text:
                                print(c("green", f"\n{text}"))
                elif isinstance(content, str):
                    if content:
                        print(c("green", f"\n{content}"))
        except Exception as e:
            print(c("red", f"\n[错误] {e}"))
            import traceback
            traceback.print_exc()


# ═══════════════════════════════════════════════
# 单次查询模式
# ═══════════════════════════════════════════════

def single_query_mode(query: str):
    """执行一次查询并打印结果"""
    print(c("dim", f"[单次查询] 问题: {query}\n"))
    history = [{"role": "user", "content": query}]
    try:
        agent_loop(history)
        last_msg = history[-1] if history else None
        if last_msg:
            content = last_msg.get("content", "")
            if isinstance(content, list):
                for block in content:
                    if getattr(block, "type", None) == "text":
                        text = block.text
                        if text:
                            print(c("green", text))
            elif isinstance(content, str):
                if content:
                    print(c("green", content))
    except Exception as e:
        print(c("red", f"\n[错误] {e}"))
        sys.exit(1)


# ═══════════════════════════════════════════════
# 参数解析 & 入口
# ═══════════════════════════════════════════════

def _safe(text: str) -> str:
    """去除可能引发编码错误的字符，适配 Windows GBK 终端"""
    try:
        text.encode(sys.stdout.encoding or "utf-8")
        return text
    except UnicodeEncodeError:
        return text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8"
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=_safe("Learning Manager Agent - 终端调试入口"),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_safe("""
使用示例:
  python -m src.ui.cli                               # 交互模式
  python -m src.ui.cli "帮我制定雅思学习计划"         # 单次查询
  python -m src.ui.cli -q "学了听力"                  # 单次查询（短参数）
  python -m src.ui.cli --history                      # 查看记忆索引
  python -m src.ui.cli --memories                     # 列出所有记忆文件
        """),
    )

    # 互斥组：不能同时指定 query 和 --history/--memories
    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "query",
        nargs="?",
        type=str,
        default=None,
        metavar="问题",
        help="直接传入问题，以单次查询模式运行（不进入交互模式）",
    )

    group.add_argument(
        "-q", "--query",
        type=str,
        dest="query_short",
        default=None,
        metavar="问题",
        help="单次查询模式的短参数形式",
    )

    group.add_argument(
        "--history",
        action="store_true",
        help="查看记忆索引后退出",
    )

    group.add_argument(
        "--memories",
        action="store_true",
        help="列出所有记忆文件后退出",
    )

    parser.add_argument(
        "--read",
        type=str,
        default=None,
        metavar="文件名",
        help="读取指定记忆文件后退出",
    )

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    # --read 参数是独立的（不与其他互斥）
    if args.read:
        cmd_read(args.read)
        return

    if args.history:
        cmd_history()
        return

    if args.memories:
        cmd_memories()
        return

    # 单次查询（两种方式）
    query_text = args.query or args.query_short
    if query_text:
        single_query_mode(query_text)
        return

    # 默认：交互模式
    interactive_mode()


if __name__ == "__main__":
    main()
