"""
Export the whole memory as plain files: Markdown for reading, JSON for
machines, and every original file — readable without this app.

Honesty travels with the data: uncertain memories stay marked as
uncertain, and every source is listed.
"""

import io
import json
import re
import zipfile
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.storage import get_storage
from app.models import Memory
from app.schemas import MemoryRead


def _slug(text: str) -> str:
    """A filename-safe version of a title (non-Latin titles fall back to 'memory')."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "memory"


def _memory_markdown(memory: Memory, files_by_attachment: dict) -> str:
    lines = [f"# {memory.title}", ""]
    lines.append(f"- **Date:** {memory.occurred_on}")
    lines.append(f"- **Type:** {memory.memory_type}")
    if memory.confidence == "uncertain":
        lines.append("- **Confidence:** ⚠️ uncertain — recorded with doubt; not confirmed")
    else:
        lines.append("- **Confidence:** confirmed")
    if memory.topics:
        lines.append("- **Topics:** " + " ".join(f"#{t}" for t in memory.topics))
    lines.append(f"- **Language:** {memory.language}")
    if memory.project:
        lines.append(f"- **Project:** {memory.project}")
    lines += ["", "## What you recorded", "", memory.content, ""]

    if memory.evidence:
        lines += ["## Sources", ""]
        for ev in memory.evidence:
            entry = f"- **{ev.source_type}**"
            if ev.source_detail:
                entry += f" — {ev.source_detail}"
            lines.append(entry)
            if ev.excerpt and ev.excerpt.strip() != memory.content.strip():
                excerpt = ev.excerpt.strip().replace("\n", "\n  > ")
                lines.append(f"  > {excerpt}")
        lines.append("")

    if memory.attachments:
        lines += ["## Original files", ""]
        for att in memory.attachments:
            path = files_by_attachment.get(att.id)
            if path:
                lines.append(f"- [{att.original_filename}](../{path})")
            else:
                lines.append(f"- {att.original_filename} — ⚠️ missing from storage at export time")
        lines.append("")

    return "\n".join(lines)


def build_export(db: Session) -> tuple[bytes, str]:
    """Build the export zip. Returns (zip bytes, suggested filename)."""
    memories = db.execute(
        select(Memory)
        .options(selectinload(Memory.evidence), selectinload(Memory.attachments))
        .order_by(Memory.occurred_on.desc(), Memory.created_at.desc())
    ).scalars().all()

    storage = get_storage()
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%d")

    buffer = io.BytesIO()
    missing: list[str] = []
    files_written: dict[str, str] = {}  # storage key → path in zip
    files_by_attachment: dict = {}      # attachment id → path in zip

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Original files, each written once even if shared.
        for memory in memories:
            for att in memory.attachments:
                key = att.storage_key
                if key not in files_written:
                    try:
                        zf.writestr(f"files/{key}", storage.read(key))
                        files_written[key] = f"files/{key}"
                    except Exception:
                        missing.append(f"{att.original_filename} ({key})")
                        continue
                files_by_attachment[att.id] = files_written[key]

        # One readable Markdown file per memory.
        index_lines = ["# My Work Memory — all memories", "", f"Exported {now:%Y-%m-%d %H:%M} UTC.", ""]
        used_names: set[str] = set()
        for memory in memories:
            name = f"{memory.occurred_on}-{_slug(memory.title)}"
            base, n = name, 2
            while name in used_names:
                name = f"{base}-{n}"
                n += 1
            used_names.add(name)
            zf.writestr(f"memories/{name}.md", _memory_markdown(memory, files_by_attachment))
            flag = " ⚠️" if memory.confidence == "uncertain" else ""
            index_lines.append(f"- {memory.occurred_on} — [{memory.title}](memories/{name}.md){flag}")
        zf.writestr("index.md", "\n".join(index_lines) + "\n")

        # Everything, machine-readable.
        data = [MemoryRead.model_validate(m).model_dump(mode="json") for m in memories]
        zf.writestr("memories.json", json.dumps(data, ensure_ascii=False, indent=2))

        readme = [
            "# My Work Memory — export",
            "",
            f"Exported {now:%Y-%m-%d %H:%M} UTC · {len(memories)} memories · {len(files_written)} files.",
            "",
            "- `index.md` — every memory, newest first",
            "- `memories/` — one Markdown file per memory: what you recorded, its sources and files",
            "- `memories.json` — the same data, machine-readable",
            "- `files/` — every original file, exactly as uploaded",
            "",
            "Memories marked ⚠️ were recorded with uncertainty and were never confirmed.",
            "AI-proposed titles, types and topics are labelled as such in each memory's sources;",
            "the text under 'What you recorded' is always your own words.",
        ]
        if missing:
            readme += ["", "## Files missing from storage at export time", ""] + [f"- {m}" for m in missing]
        zf.writestr("README.md", "\n".join(readme) + "\n")

    return buffer.getvalue(), f"my-work-memory-{stamp}.zip"