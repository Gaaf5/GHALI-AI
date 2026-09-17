import json
from pathlib import Path

from .store import KnowledgeDocument, KnowledgeStore


def load_json(path: str | Path) -> str:
    file_path = Path(path)
    data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    return json.dumps(data, ensure_ascii=False, indent=2)


def ingest_json(path: str | Path, store: KnowledgeStore, source: str = "user_uploaded") -> Path:
    file_path = Path(path)
    content = load_json(file_path)
    data = json.loads(content)
    title = data.get("title") or file_path.stem.replace("_", " ").title()
    existing = store.find_duplicate_content(content)
    if existing:
        return existing[0]
    return store.add(KnowledgeDocument(
        title=title,
        content=content,
        source=source,
        document_type="json",
    ))
