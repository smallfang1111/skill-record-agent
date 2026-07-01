"""
Memory system - Persistent, cross-session knowledge for the coding agent.

Storage:
    .memory/
      MEMORY.md              ← index (one line per memory, ≤200 lines)
      feedback_tabs.md       ← individual memory files (Markdown + YAML frontmatter)
      user_profile.md
      project_facts.md

Flow in agent_loop:
    1. Load MEMORY.md index into SYSTEM prompt (cheap, always present)
    2. Select relevant memories by filename/description → inject content
    3. Run compression pipeline from s08
    4. After each turn ends → extract new memories from original messages
    5. Periodically consolidate (Dream)
"""

import os, json, time, re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKDIR = Path.cwd()
MEMORY_DIR = WORKDIR / ".memory"
MEMORY_DIR.mkdir(exist_ok=True)
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"

MEMORY_TYPES = ["user", "feedback", "project", "reference"]
CONSOLIDATE_THRESHOLD = 10

# ---------------------------------------------------------------------------
# YAML frontmatter helpers
# ---------------------------------------------------------------------------
def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from a memory file."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, parts[2].strip()


def _build_frontmatter(name: str, description: str, mem_type: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\ntype: {mem_type}\n---\n\n"


# ---------------------------------------------------------------------------
# CRUD on memory files
# ---------------------------------------------------------------------------
def write_memory_file(name: str, mem_type: str, description: str, body: str) -> Path:
    """Write a single memory file with YAML frontmatter."""
    slug = name.lower().replace(" ", "-").replace("/", "-")
    filename = f"{slug}.md"
    filepath = MEMORY_DIR / filename
    content = _build_frontmatter(name, description, mem_type) + body + "\n"
    filepath.write_text(content, encoding='utf-8')
    _rebuild_index()
    return filepath


def _rebuild_index():
    """Rebuild MEMORY.md index from all memory files."""
    lines = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        meta, body = _parse_frontmatter(raw)
        name = meta.get("name", f.stem)
        desc = meta.get("description", body.split("\n")[0][:80])
        lines.append(f"- [{name}]({f.name}) — {desc}")
    try:
        MEMORY_INDEX.write_text("\n".join(lines) + "\n" if lines else "", encoding='utf-8')
    except Exception:
        pass


def read_memory_index() -> str:
    """Read MEMORY.md index (injected into SYSTEM every turn)."""
    if not MEMORY_INDEX.exists():
        return ""
    try:
        text = MEMORY_INDEX.read_text(encoding='utf-8', errors='replace').strip()
    except Exception:
        return ""
    return text if text else ""


def read_memory_file(filename: str) -> Optional[str]:
    """Read a single memory file's full content."""
    path = MEMORY_DIR / filename
    if not path.exists():
        return None
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None


def delete_memory_file(filename: str) -> bool:
    """Delete a memory file and rebuild index."""
    path = MEMORY_DIR / filename
    if path.exists() and path.name != "MEMORY.md":
        path.unlink()
        _rebuild_index()
        return True
    return False


def list_memory_files() -> list[dict]:
    """List all memory files with metadata."""
    result = []
    for f in sorted(MEMORY_DIR.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        try:
            raw = f.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        meta, body = _parse_frontmatter(raw)
        result.append({
            "filename": f.name,
            "name": meta.get("name", f.stem),
            "description": meta.get("description", ""),
            "type": meta.get("type", "user"),
            "body": body,
        })
    return result


def get_memory_stats() -> dict:
    """Get statistics about stored memories."""
    files = list_memory_files()
    total_lines = 0
    total_chars = 0
    type_counts = {}
    for f in files:
        total_lines += f["body"].count("\n") + 1
        total_chars += len(f["body"])
        t = f["type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    return {
        "total_files": len(files),
        "total_lines": total_lines,
        "total_chars": total_chars,
        "type_counts": type_counts,
    }


# ---------------------------------------------------------------------------
# Relevance selection (LLM-based + keyword fallback)
# ---------------------------------------------------------------------------
def select_relevant_memories(messages: list, max_items: int = 5) -> list[str]:
    """Select relevant memory filenames by matching recent conversation against
    memory names/descriptions. Uses a simple LLM call (or falls back to keyword
    matching on name+description)."""
    files = list_memory_files()
    if not files:
        return []

    # Collect recent user text for context
    recent_texts = []
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    str(getattr(b, "text", "")) for b in content
                    if getattr(b, "type", None) == "text"
                )
            if isinstance(content, str):
                recent_texts.append(content)
            if len(recent_texts) >= 3:
                break
    recent = " ".join(reversed(recent_texts))[:2000]

    if not recent.strip():
        return []

    # Try LLM-based selection if client is available
    try:
        from anthropic import Anthropic
        from dotenv import load_dotenv
        load_dotenv(override=True)

        catalog_lines = []
        for i, f in enumerate(files):
            catalog_lines.append(f"{i}: {f['name']} — {f['description']}")
        catalog = "\n".join(catalog_lines)

        prompt = (
            "Given the recent conversation and the memory catalog below, "
            "select the indices of memories that are clearly relevant. "
            "Return ONLY a JSON array of integers, e.g. [0, 3]. "
            "If none are relevant, return [].\n\n"
            f"Recent conversation:\n{recent}\n\n"
            f"Memory catalog:\n{catalog}"
        )

        client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
        model = os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
        )
        # 添加这几行来查看缓存命中情况
        print(response.usage)
        # 或者分别打印
        print(f"缓存命中的 tokens7: {response.usage.prompt_cache_hit_tokens}")
        print(f"缓存未命中的 tokens7: {response.usage.prompt_cache_miss_tokens}")
        text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content)
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            indices = json.loads(match.group())
            selected = []
            for idx in indices:
                if isinstance(idx, int) and 0 <= idx < len(files):
                    selected.append(files[idx]["filename"])
                    if len(selected) >= max_items:
                        break
            return selected
    except Exception:
        pass

    # Fallback: keyword matching on name + description
    keywords = [w.lower() for w in recent.split() if len(w) > 3]
    selected = []
    for f in files:
        text = (f["name"] + " " + f["description"]).lower()
        if any(kw in text for kw in keywords):
            selected.append(f["filename"])
            if len(selected) >= max_items:
                break
    return selected


# ---------------------------------------------------------------------------
# High-level helpers for the agent loop
# ---------------------------------------------------------------------------
def load_memories(messages: list) -> str:
    """Load relevant memory content for injection into context."""
    selected_files = select_relevant_memories(messages)
    if not selected_files:
        return ""

    parts = ["<relevant_memories>"]
    for filename in selected_files:
        content = read_memory_file(filename)
        if content:
            parts.append(content)
    parts.append("</relevant_memories>")
    return "\n\n".join(parts)


def extract_memories(messages: list):
    """Extract new memories from recent dialogue. Runs after each turn."""
    # Collect recent conversation text
    dialogue_parts = []
    for msg in messages[-10:]:
        role = msg.get("role", "?")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(
                str(getattr(b, "text", "")) for b in content
                if getattr(b, "type", None) == "text"
            )
        if isinstance(content, str) and content.strip():
            dialogue_parts.append(f"[{role}]: {content[:500]}")

    dialogue = "\n".join(dialogue_parts)
    if len(dialogue) < 50:
        return  # Not enough dialogue to extract from

    # Use LLM to extract new memories
    try:
        from anthropic import Anthropic
        from dotenv import load_dotenv
        load_dotenv(override=True)

        existing = list_memory_files()
        existing_summary = "\n".join(
            f"- {f['name']} ({f['type']}): {f['description']}"
            for f in existing
        ) or "None yet."

        prompt = (
            "Extract NEW memories from the recent dialogue that are worth remembering across sessions.\n\n"
            "Rules:\n"
            "1. Only extract information that is DIFFERENT from existing memories.\n"
            "2. Possible types: user (preferences, goals), project (code decisions, bugs), reference (links, docs).\n"
            "3. If nothing new, return an empty JSON array.\n"
            "4. Return a JSON array of objects: {name, type, description, body}\n\n"
            f"Existing memories:\n{existing_summary}\n\n"
            f"Recent dialogue:\n{dialogue}"
        )

        client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
        model = os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )
        # 添加这几行来查看缓存命中情况
        print(response.usage)
        # 或者分别打印
        print(f"缓存命中的 tokens8: {response.usage.prompt_cache_hit_tokens}")
        print(f"缓存未命中的 tokens8: {response.usage.prompt_cache_miss_tokens}")
        text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content)
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            new_memories = json.loads(match.group())
            for mem in new_memories:
                write_memory_file(
                    name=mem.get("name", "untitled"),
                    mem_type=mem.get("type", "user"),
                    description=mem.get("description", ""),
                    body=mem.get("body", ""),
                )
    except Exception:
        pass


def consolidate_memories():
    """Consolidate memories when there are too many. Merges similar memories."""
    files = list_memory_files()
    if len(files) < CONSOLIDATE_THRESHOLD:
        return

    # Group by type
    by_type: dict[str, list] = {}
    for f in files:
        t = f["type"]
        by_type.setdefault(t, []).append(f)

    # If any type has more than threshold/2 items, consolidate that type
    for mem_type, items in by_type.items():
        if len(items) < CONSOLIDATE_THRESHOLD // 2:
            continue

        summary = "\n\n".join(
            f"## {f['name']}\n{f['body']}"
            for f in items
        )

        try:
            from anthropic import Anthropic
            from dotenv import load_dotenv
            load_dotenv(override=True)

            prompt = (
                f"Consolidate the following {mem_type} memories into a single, concise memory file. "
                "Remove redundancy, keep unique facts, and preserve important details.\n\n"
                f"{summary}\n\n"
                "Return a JSON object: {name, description, body}"
            )

            client = Anthropic(base_url=os.getenv("ANTHROPIC_BASE_URL"))
            model = os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")
            response = client.messages.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            # 添加这几行来查看缓存命中情况
            print(response.usage)
            # 或者分别打印
            print(f"缓存命中的 tokens8: {response.usage.prompt_cache_hit_tokens}")
            print(f"缓存未命中的 tokens8: {response.usage.prompt_cache_miss_tokens}")
            text = response.content[0].text if hasattr(response.content[0], 'text') else str(response.content)
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                consolidated = json.loads(match.group())
                # Write consolidated memory
                write_memory_file(
                    name=consolidated.get("name", f"{mem_type}-consolidated"),
                    mem_type=mem_type,
                    description=consolidated.get("description", f"Consolidated {mem_type} memories"),
                    body=consolidated.get("body", ""),
                )
                # Remove old files
                for f in items:
                    delete_memory_file(f["filename"])
        except Exception:
            pass
