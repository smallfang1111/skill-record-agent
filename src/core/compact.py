"""
compact.py — Context compaction pipeline

Provides functions to keep messages within context limits:
  - snip_compact: remove old messages
  - micro_compact: shorten old tool results
  - persist_large: save large outputs to files
  - tool_result_budget: budget for tool results
  - summarize_history: LLM summarization
  - compact_history: full compaction
  - reactive_compact: emergency compaction on prompt_too_long
  - sanitize_tool_results: remove orphaned tool_result blocks
  - write_transcript: save transcript to disk
  - estimate_size: rough size estimation
"""

import json
import time
from pathlib import Path

from .memory import WORKDIR, TRANSCRIPT_DIR, TOOL_RESULTS_DIR, client, MODEL, extract_text

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

CONTEXT_LIMIT = 50000
KEEP_RECENT = 3
PERSIST_THRESHOLD = 30000


# ═══════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════

def estimate_size(msgs: list) -> int:
    """Rough size estimation of messages in characters."""
    return len(str(msgs))


def write_transcript(msgs: list) -> Path:
    """Write a transcript of the current messages to disk."""
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    p = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with p.open("w", encoding='utf-8') as f:
        for m in msgs:
            f.write(json.dumps(m, default=str) + "\n")
    return p


# ═══════════════════════════════════════════════════════════
# Block-level utilities (dict & SDK object compatible)
# ═══════════════════════════════════════════════════════════

def _get_block_type(block):
    """统一获取 block 的类型，支持 dict 和 Anthropic SDK 对象"""
    if isinstance(block, dict):
        return block.get("type", "")
    return getattr(block, "type", "")


def _get_block_id(block):
    """统一获取 tool_use block 的 id，支持 dict 和 Anthropic SDK 对象"""
    if isinstance(block, dict):
        return block.get("tool_use_id") or block.get("id", "")
    return getattr(block, "id", "")


def _get_tool_use_id(block):
    """统一获取 tool_result block 引用的 tool_use_id，支持 dict 和 Anthropic SDK 对象"""
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


# ═══════════════════════════════════════════════════════════
# Snip compact — remove oldest messages
# ═══════════════════════════════════════════════════════════

def snip_compact(msgs: list, mx: int = 50) -> list:
    """Keep at most mx messages: first 3 (system/context) + last (mx-3)."""
    if len(msgs) <= mx:
        return msgs
    return msgs[:3] + [
        {"role": "user", "content": f"[snipped {len(msgs) - mx} msgs]"}
    ] + msgs[-(mx - 3):]


# ═══════════════════════════════════════════════════════════
# Micro compact — shorten old tool results
# ═══════════════════════════════════════════════════════════

def collect_tool_results(msgs: list) -> list:
    """Collect all tool_result blocks across all messages.
    Returns list of (msg_index, block_index, block)."""
    blocks = []
    for mi, msg in enumerate(msgs):
        if msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        for bi, block in enumerate(msg["content"]):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                blocks.append((mi, bi, block))
    return blocks


def micro_compact(msgs: list) -> list:
    """Shorten old tool results, keeping only the most recent KEEP_RECENT ones."""
    tr = collect_tool_results(msgs)
    if len(tr) <= KEEP_RECENT:
        return msgs
    for _, _, b in tr[:-KEEP_RECENT]:
        if len(b.get("content", "")) > 120:
            b["content"] = "[Earlier tool result compacted.]"
    return msgs


# ═══════════════════════════════════════════════════════════
# Persist large — save big outputs to disk
# ═══════════════════════════════════════════════════════════

def persist_large(tid: str, out: str) -> str:
    """If output exceeds PERSIST_THRESHOLD, save full version to a file
    and return a short preview."""
    if len(out) <= PERSIST_THRESHOLD:
        return out
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    p = TOOL_RESULTS_DIR / f"{tid}.txt"
    if not p.exists():
        p.write_text(out, encoding='utf-8')
    return f"<persisted-output>\nFull: {p}\nPreview:\n{out[:2000]}\n</persisted-output>"


def tool_result_budget(msgs: list, mx: int = 200_000) -> list:
    """Persist large tool results in the last user message if total exceeds mx."""
    last = msgs[-1] if msgs else None
    if not last or last.get("role") != "user" or not isinstance(last.get("content"), list):
        return msgs

    blocks = [
        (i, b) for i, b in enumerate(last["content"])
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
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


# ═══════════════════════════════════════════════════════════
# LLM-based summarization
# ═══════════════════════════════════════════════════════════

def summarize_history(msgs: list) -> str:
    """Use the LLM to produce a compact summary of the conversation so far."""
    conv = json.dumps(msgs, default=str)[:80000]
    response = client.messages.create(
        model=MODEL,
        messages=[{
            "role": "user",
            "content": (
                "Summarize this coding-agent conversation so work can continue.\n"
                "Preserve: 1. current goal, 2. key findings, 3. files changed, "
                "4. remaining work, 5. user constraints.\n\n" + conv
            )
        }],
        max_tokens=2000,
    )
    
    # 添加这几行来查看缓存命中情况
    print(response.usage,'6')
    return extract_text(response.content).strip()


def compact_history(msgs: list) -> list:
    """Full compaction: write transcript, summarize, return single message."""
    write_transcript(msgs)
    summary = summarize_history(msgs)
    return [{"role": "user", "content": f"[Compacted]\n\n{summary}"}]


def reactive_compact(msgs: list) -> list:
    """Emergency compaction: write transcript, summarize, keep last 5 messages."""
    write_transcript(msgs)
    summary = summarize_history(msgs)
    return [{"role": "user", "content": f"[Reactive compact]\n\n{summary}"}, *msgs[-5:]]
