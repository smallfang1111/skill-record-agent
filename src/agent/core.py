"""
核心模块

包含 agent_loop（主循环）和压缩管道（context compaction）。
"""

import os
import json
import time
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# 配置
WORKDIR = Path.cwd()
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"

client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")

# 导入工具和记忆模块
from src.agent.tools import TOOLS, TOOL_HANDLERS, extract_text
from src.agent.memory import (
    build_system, load_memories, extract_memories,
    consolidate_memories, read_memory_index
)


# ═══════════════════════════════════════════════
# 压缩管道（来自 s08）
# ═══════════════════════════════════════════════

CONTEXT_LIMIT = 50000
KEEP_RECENT = 3
PERSIST_THRESHOLD = 30000


def estimate_size(msgs):
    """估算消息列表的大小（字符数）"""
    return len(str(msgs))


def snip_compact(msgs, mx=50):
    """裁剪中间的消息，只保留开头和结尾"""
    if len(msgs) <= mx:
        return msgs
    return msgs[:3] + [{"role": "user", "content": f"[snipped {len(msgs)-mx} msgs]"}] + msgs[-(mx-3):]


def collect_tool_results(msgs):
    """收集所有 tool_result 块的位置"""
    blocks = []
    for mi, msg in enumerate(msgs):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        for bi, block in enumerate(msg["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                blocks.append((mi, bi, block))
    return blocks


def micro_compact(msgs):
    """压缩早期的 tool_result 块（只保留最近的 KEEP_RECENT 个）"""
    tr = collect_tool_results(msgs)
    if len(tr) <= KEEP_RECENT:
        return msgs
    for _, _, b in tr[:-KEEP_RECENT]:
        if len(b.get("content", "")) > 120:
            b["content"] = "[Earlier tool result compacted.]"
    return msgs


def persist_large(tid, out):
    """将过大的 tool_result 持久化到文件"""
    if len(out) <= PERSIST_THRESHOLD:
        return out
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    p = TOOL_RESULTS_DIR / f"{tid}.txt"
    if not p.exists():
        p.write_text(out, encoding='utf-8')
    return f"<persisted-output>\nFull: {p}\nPreview:\n{out[:2000]}\n</persisted-output>"


def tool_result_budget(msgs, mx=200_000):
    """限制最后一个 user 消息中 tool_result 的总大小"""
    last = msgs[-1] if msgs else None
    if not last or last.get("role") != "user" or not isinstance(last.get("content"), list):
        return msgs
    blocks = [(i, b) for i, b in enumerate(last["content"]) if isinstance(b, dict) and b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= mx:
        return msgs
    for _, block in sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True):
        if total <= mx:
            break
        c = str(block.get("content", ""))
        if len(c) <= PERSIST_THRESHOLD:
            continue
        block["content"] = persist_large(block.get("tool_use_id", "?"), c)
        total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    return msgs


def write_transcript(msgs):
    """将消息列表写入 transcript 文件"""
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    p = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with p.open("w") as f:
        for m in msgs:
            f.write(json.dumps(m, default=str) + "\n")
    return p


def summarize_history(msgs):
    """使用 LLM 总结对话历史"""
    conv = json.dumps(msgs, default=str)[:80000]
    r = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this coding-agent conversation so work can continue.\n"
            "Preserve: 1. current goal, 2. key findings, 3. files changed, 4. remaining work, 5. user constraints.\n\n" + conv}],
        max_tokens=2000
    )
    return extract_text(r.content).strip()


def compact_history(msgs):
    """压缩历史消息（自动触发）"""
    write_transcript(msgs)
    summary = summarize_history(msgs)
    return [{"role": "user", "content": f"[Compacted]\n\n{summary}"}]


def reactive_compact(msgs):
    """响应式压缩（当 prompt 过长时触发）"""
    write_transcript(msgs)
    summary = summarize_history(msgs)
    return [{"role": "user", "content": f"[Reactive compact]\n\n{summary}"}, *msgs[-5:]]


# ═══════════════════════════════════════════════
# 清理孤立的 tool_result 块
# ═══════════════════════════════════════════════

def _get_block_type(block):
    """统一获取 block 的类型，支持 dict 和 Anthropic SDK 对象"""
    if isinstance(block, dict):
        return block.get("type", "")
    return getattr(block, "type", "")


def _get_block_id(block):
    """统一获取 tool_use block 的 id"""
    if isinstance(block, dict):
        return block.get("tool_use_id") or block.get("id", "")
    return getattr(block, "id", "")


def _get_tool_use_id(block):
    """统一获取 tool_result block 引用的 tool_use_id"""
    if isinstance(block, dict):
        return block.get("tool_use_id", "")
    return getattr(block, "tool_use_id", "")


def _collect_tool_use_ids(msgs: list) -> set:
    """收集所有消息中 tool_use 块的 id"""
    ids = set()
    for msg in msgs:
        content = msg.get("content", [])
        if isinstance(content, list):
            for block in content:
                if _get_block_type(block) == "tool_use":
                    ids.add(_get_block_id(block))
    return ids


def sanitize_tool_results(msgs: list) -> None:
    """移除没有对应 tool_use 的孤立 tool_result 块，并删除变空的消息。
    
    压缩操作（snip/micro/compact）可能删除了包含 tool_use 的 assistant 消息，
    导致后续 user 消息中的 tool_result 引用了不存在的 tool_use_id，
    这会触发 API 的 invalid_request_error。
    
    同时，如果某条消息被清空了所有 content，也一并删除，
    避免 "all messages must have non-empty content" 错误。
    """
    valid_ids = _collect_tool_use_ids(msgs)
    # 第一遍：清理孤立 tool_result
    for msg in msgs:
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        new_content = []
        for block in content:
            if _get_block_type(block) == "tool_result":
                tid = _get_tool_use_id(block)
                if tid not in valid_ids:
                    continue  # 丢弃孤立的 tool_result
            new_content.append(block)
        msg["content"] = new_content
    # 第二遍：移除 content 为空的非法消息（原地操作）
    msgs[:] = [
        m for m in msgs
        if not (
            isinstance(m.get("content"), list) and len(m["content"]) == 0
        )
        and not (
            isinstance(m.get("content"), str) and not m["content"].strip()
        )
    ]


# ═══════════════════════════════════════════════
# agent_loop — 主循环
# ═══════════════════════════════════════════════

MAX_REACTIVE_RETRIES = 1


def agent_loop(messages: list):
    """运行 agent 主循环。
    
    流程：
    1. 加载相关记忆注入上下文
    2. 压缩管道（budget → snip → micro）
    3. 调用 LLM API
    4. 处理工具调用
    5. 提取新记忆
    """
    reactive_retries = 0
    # 注入相关记忆内容到当前 user turn
    memories_content = load_memories(messages)
    memory_turn = len(messages) - 1 if messages and isinstance(messages[-1].get("content"), str) else None
    while True:
        # 重建 system prompt（包含最新记忆索引）
        system = build_system()

        # 保存压缩前的快照，用于后续记忆提取
        pre_compress = [m if isinstance(m, dict) else {"role": m.get("role",""),
            "content": str(m.get("content",""))} for m in messages]

        # 压缩管道
        messages[:] = tool_result_budget(messages)
        messages[:] = snip_compact(messages)
        messages[:] = micro_compact(messages)

        if estimate_size(messages) > CONTEXT_LIMIT:
            print("[auto compact]")
            messages[:] = compact_history(messages)

        # 清理压缩后可能产生的孤立 tool_result 块
        sanitize_tool_results(messages)

        try:
            request_messages = messages
            if memories_content and memory_turn is not None and memory_turn < len(messages):
                request_messages = messages.copy()
                request_messages[memory_turn] = {
                    **messages[memory_turn],
                    "content": memories_content + "\n\n" + messages[memory_turn]["content"],
                }
            response = client.messages.create(
                model=MODEL, system=system, messages=request_messages, tools=TOOLS, max_tokens=8000
            )
            # 添加这几行来查看缓存命中情况
            print(response.usage,'1')
            reactive_retries = 0
        except Exception as e:
            if ("prompt_too_long" in str(e).lower() or "too many tokens" in str(e).lower()) and reactive_retries < MAX_REACTIVE_RETRIES:
                print("[reactive compact]")
                messages[:] = reactive_compact(messages)
                reactive_retries += 1
                continue
            raise

        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":
            # 从压缩前快照中提取记忆（保持完整性）
            extract_memories(pre_compress)
            consolidate_memories()
            return

        # 处理工具调用结果
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"\033[36m> {block.name}\033[0m")
            handler = TOOL_HANDLERS.get(block.name)
            output = handler(**block.input) if handler else f"Unknown: {block.name}"
            print(str(output)[:200])
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        messages.append({"role": "user", "content": results})
