"""
Parse fenced code blocks out of LLM output and write them as real files to a
per-run workspace directory.

Filename inference order:
  1. A header line within the previous 4 lines of the block that matches
     "filename: name.ext", "## name.ext", or "name.ext" alone.
  2. The first line inside the block, if it is a comment containing a
     "name.ext" token (e.g. "# parser.py", "// app.js", "-- create_users.sql").
  3. Fallback: file{N}.{ext} where ext is derived from the fence language tag.

Prose (anything outside fences) is also written to README.md alongside the
files, so the human can read the LLM's plan plus the artifacts in one place.
"""
import logging
import os
import re

log = logging.getLogger("openclaw.codeblocks")

# Map fence language tags to file extensions.
LANG_EXT = {
    "python": "py", "py": "py", "py3": "py",
    "javascript": "js", "js": "js", "node": "js",
    "typescript": "ts", "ts": "ts",
    "tsx": "tsx", "jsx": "jsx",
    "bash": "sh", "sh": "sh", "shell": "sh", "zsh": "sh",
    "go": "go", "golang": "go",
    "rust": "rs", "rs": "rs",
    "sql": "sql", "postgres": "sql", "psql": "sql",
    "yaml": "yaml", "yml": "yaml",
    "json": "json",
    "toml": "toml",
    "html": "html",
    "css": "css",
    "scss": "scss",
    "markdown": "md", "md": "md",
    "java": "java",
    "kotlin": "kt", "kt": "kt",
    "c": "c", "cpp": "cpp", "c++": "cpp", "cc": "cpp",
    "ruby": "rb", "rb": "rb",
    "php": "php",
    "dockerfile": "Dockerfile",
    "make": "Makefile", "makefile": "Makefile",
    "ini": "ini", "conf": "conf", "config": "conf",
    "env": "env",
    "csv": "csv",
    "xml": "xml",
    "swift": "swift",
}

FENCE_RE = re.compile(r"```([\w+#.-]+)?\n(.*?)```", re.DOTALL)
FILENAME_HINT_RE = re.compile(r"([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)")
# Comments in first line that often carry a filename.
COMMENT_PREFIXES = ("# ", "// ", "-- ", "/* ", "; ", "<!-- ")

SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_./-]")


def _safe_name(name: str) -> str:
    """Strip anything unsafe; refuse traversal."""
    if "/" in name and (".." in name or name.startswith("/")):
        return ""
    return SAFE_NAME_RE.sub("_", name).strip("_")


def _filename_from_header(text_before: str) -> str | None:
    """Look at the last few lines before the fence for a filename hint."""
    tail = text_before.splitlines()[-4:]
    for line in reversed(tail):
        line = line.strip().lstrip("#*").strip(" *`:")
        if not line:
            continue
        # Patterns: "filename: parser.py", "parser.py", "## parser.py"
        m = re.search(r"(?:filename\s*:\s*)?([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)", line)
        if m:
            cand = _safe_name(m.group(1))
            if cand and "." in cand:
                return cand
    return None


def _filename_from_first_line(body: str) -> str | None:
    first = body.lstrip().splitlines()[0] if body.strip() else ""
    if not any(first.lstrip().startswith(p) for p in COMMENT_PREFIXES):
        return None
    m = FILENAME_HINT_RE.search(first)
    if not m:
        return None
    cand = _safe_name(m.group(1))
    return cand if cand and "." in cand else None


def parse_blocks(text: str) -> tuple[list[dict], str]:
    """
    Returns (blocks, readme_prose).
      blocks: [{filename, language, body, source: 'header'|'first_line'|'fallback'}, ...]
      readme_prose: text with fences stripped, suitable for a README.
    """
    blocks: list[dict] = []
    seen_names: dict[str, int] = {}
    last_end = 0
    prose_parts: list[str] = []
    fallback_counter = 0

    for m in FENCE_RE.finditer(text):
        prose_parts.append(text[last_end:m.start()])
        last_end = m.end()
        lang = (m.group(1) or "").lower().strip()
        body = m.group(2)
        ext = LANG_EXT.get(lang, "txt")

        # Filename inference
        header_name = _filename_from_header(text[:m.start()])
        first_line_name = _filename_from_first_line(body)
        if header_name:
            fname, source = header_name, "header"
        elif first_line_name:
            fname, source = first_line_name, "first_line"
        else:
            fallback_counter += 1
            base = "Dockerfile" if ext == "Dockerfile" else (
                "Makefile" if ext == "Makefile" else f"file{fallback_counter}.{ext}"
            )
            fname, source = base, "fallback"

        # de-duplicate
        if fname in seen_names:
            seen_names[fname] += 1
            stem, dot, e = fname.rpartition(".")
            fname = f"{stem}_{seen_names[fname]}.{e}" if dot else f"{fname}_{seen_names[fname]}"
        else:
            seen_names[fname] = 1

        blocks.append({
            "filename": fname,
            "language": lang or None,
            "body": body,
            "source": source,
            "size": len(body),
        })

    prose_parts.append(text[last_end:])
    readme = "\n".join(part.strip() for part in prose_parts if part.strip())
    return blocks, readme


def write_workspace(workspace_dir: str, prompt: str, output: str, blocks: list[dict],
                    readme_prose: str) -> list[dict]:
    """
    Write extracted blocks and a README.md to workspace_dir.
    Returns the same blocks list with `path` populated.
    """
    os.makedirs(workspace_dir, exist_ok=True)

    # README.md captures the prompt plus the prose around the code.
    readme_path = os.path.join(workspace_dir, "README.md")
    with open(readme_path, "w") as fh:
        fh.write(f"# OpenClaw run\n\n## Brief\n\n{prompt.strip()}\n\n")
        if readme_prose:
            fh.write(f"## Explanation\n\n{readme_prose}\n")
        if blocks:
            fh.write(f"\n## Files written ({len(blocks)})\n\n")
            for b in blocks:
                fh.write(f"- `{b['filename']}` ({b['language'] or 'unknown'}, {b['size']} bytes)\n")

    for b in blocks:
        path = os.path.join(workspace_dir, b["filename"])
        os.makedirs(os.path.dirname(path) or workspace_dir, exist_ok=True)
        with open(path, "w") as fh:
            fh.write(b["body"])
        b["path"] = path

    log.info("workspace %s populated: %d files + README", workspace_dir, len(blocks))
    return blocks
