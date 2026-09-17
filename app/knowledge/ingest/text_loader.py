from pathlib import Path


def load_text(path: str | Path) -> str:
    """Load a UTF-8 text document and normalize line endings."""
    text = Path(path).read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)
