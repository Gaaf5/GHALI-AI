from pathlib import Path

from .store import KnowledgeStore


class KnowledgeManager:
    """High-level helpers for inspecting and validating project knowledge."""

    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store or KnowledgeStore()

    def inventory(self) -> list[dict[str, str]]:
        items = []
        for path in self.store.list_documents():
            metadata = self.store.get_metadata(path)
            items.append({
                "file": path.name,
                "title": metadata.get("title", path.stem),
                "source": metadata.get("source", "unknown"),
                "type": metadata.get("type", "text"),
                "added": metadata.get("added", ""),
            })
        return items

    def find(self, query: str, limit: int = 5):
        return self.store.search_chunks(query, limit=limit)

    def validate(self) -> list[str]:
        issues = []
        for path in self.store.list_documents():
            text = self.store.read(path)
            metadata = self.store.get_metadata(path)
            if not text.strip():
                issues.append(f"Empty document: {path.name}")
            if not metadata.get("source"):
                issues.append(f"Missing source: {path.name}")
            if not metadata.get("title"):
                issues.append(f"Missing title: {path.name}")
            if not metadata.get("type"):
                issues.append(f"Missing type: {path.name}")
        return issues

    def details(self, filename: str) -> dict[str, str] | None:
        path = self.store.root / filename
        if not path.is_file() or path.suffix.lower() != ".txt":
            return None
        metadata = self.store.get_metadata(path)
        chunks = self.store.chunk_document(path)
        return {
            "file": path.name,
            "title": metadata.get("title", path.stem),
            "source": metadata.get("source", "unknown"),
            "type": metadata.get("type", "text"),
            "added": metadata.get("added", ""),
            "chunks": str(len(chunks)),
        }

    def remove(self, filename: str) -> bool:
        path = self.store.root / filename
        if not path.is_file() or path.suffix.lower() != ".txt":
            return False
        path.unlink()
        return True
