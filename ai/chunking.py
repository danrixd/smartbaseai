"""Text chunking for vault ingestion.

Two-tier strategy:

1. **Section split** — if the document has markdown headings (``^##``,
   ``^###``, etc.), split at heading boundaries and chunk each section
   independently. This keeps 10-K sections like *Risk Factors*, *MD&A*,
   or *Consolidated Balance Sheet* in their own chunks with the section
   title as the first line.

2. **Size-bounded packing** — within each section, pack paragraphs until
   ~``target_tokens`` words, respecting a ``MAX_CHUNK_CHARS`` hard cap.
   Oversized paragraphs (pypdf table blobs with no line breaks) are
   force-split into whitespace-aligned slices so the embedder never sees
   anything larger than the cap.

Chunk metadata shape is just a string. The caller is responsible for
attaching retrieval metadata (``{filename, section, chunk_idx, ...}``)
when it adds the chunk to a vector store. This module only cares about
producing well-shaped chunks.
"""

from __future__ import annotations

import re

MAX_CHUNK_CHARS = 2000
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _hard_split(s: str, max_chars: int) -> list[str]:
    """Force-split an oversize blob that has no paragraph breaks."""
    parts: list[str] = []
    i = 0
    while i < len(s):
        end = min(i + max_chars, len(s))
        if end < len(s):
            window_start = end - max_chars // 10
            slice_ = s[window_start:end]
            m = re.search(r"\s(?=\S*$)", slice_)
            if m:
                end = window_start + m.start()
        parts.append(s[i:end].strip())
        i = end
    return [p for p in parts if p]


def _pack_paragraphs(paragraphs: list[str], target_tokens: int) -> list[str]:
    """Greedy-pack paragraphs into chunks ~target_tokens words, capped by chars."""
    chunks: list[str] = []
    buf: list[str] = []
    size_words = 0
    size_chars = 0
    for p in paragraphs:
        if len(p) > MAX_CHUNK_CHARS:
            # Flush current buffer, then emit the hard-split pieces one at a time
            if buf:
                chunks.append("\n\n".join(buf))
                buf = []
                size_words = 0
                size_chars = 0
            for piece in _hard_split(p, MAX_CHUNK_CHARS):
                chunks.append(piece[:MAX_CHUNK_CHARS])
            continue
        words = len(p.split())
        added_chars = len(p) + 2
        if buf and (size_words + words > target_tokens or size_chars + added_chars > MAX_CHUNK_CHARS):
            chunks.append("\n\n".join(buf))
            buf = [p]
            size_words = words
            size_chars = len(p)
        else:
            buf.append(p)
            size_words += words
            size_chars += added_chars
    if buf:
        chunks.append("\n\n".join(buf))
    return [c for c in chunks if c.strip()]


def _split_into_sections(text: str) -> list[tuple[str, str]]:
    """Split a markdown document into [(section_title, section_body), ...].

    If there are no ``##`` headings at all, returns a single untitled
    section containing the whole document. This preserves the old flat
    behaviour for tenants whose files aren't markdown-with-headings.
    """
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [("", text)]

    sections: list[tuple[str, str]] = []
    # Preamble before the first heading (if any) is kept as an untitled section
    first_start = matches[0].start()
    if first_start > 0:
        preamble = text[:first_start].strip()
        if preamble:
            sections.append(("", preamble))

    for idx, m in enumerate(matches):
        title = m.group(2).strip()
        body_start = m.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        if not body:
            continue
        sections.append((title, body))
    return sections


def chunk_text(text: str, target_tokens: int = 500) -> list[str]:
    """Return a list of chunks (pure strings) ready for the embedder.

    Each chunk is prefixed with the section title (as a bold line) when
    the document has markdown headings — this biases semantic similarity
    toward matching the section name.
    """
    sections = _split_into_sections(text)
    out: list[str] = []
    for title, body in sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        if not paragraphs:
            continue
        packed = _pack_paragraphs(paragraphs, target_tokens)
        for chunk in packed:
            if title:
                out.append(f"**{title}**\n\n{chunk}"[:MAX_CHUNK_CHARS])
            else:
                out.append(chunk[:MAX_CHUNK_CHARS])
    return out


def chunk_with_sections(text: str, target_tokens: int = 500) -> list[dict]:
    """Like ``chunk_text`` but returns rich dicts with section metadata.

    Output: ``[{"text": str, "section": str, "chunk_idx": int}, ...]``
    """
    sections = _split_into_sections(text)
    out: list[dict] = []
    for title, body in sections:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        if not paragraphs:
            continue
        packed = _pack_paragraphs(paragraphs, target_tokens)
        for i, chunk in enumerate(packed):
            full = f"**{title}**\n\n{chunk}" if title else chunk
            out.append(
                {
                    "text": full[:MAX_CHUNK_CHARS],
                    "section": title,
                    "chunk_idx": len(out),
                }
            )
    return out
