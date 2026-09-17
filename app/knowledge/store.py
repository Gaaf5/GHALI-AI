from dataclasses import dataclass
from pathlib import Path
import re
from datetime import datetime, timezone

from .chunking import KnowledgeChunk, split_text
from app.core.settings import KNOWLEDGE_PATH


@dataclass(frozen=True)
class KnowledgeDocument:
    title: str
    content: str
    source: str = "manual"
    document_type: str = "text"


class KnowledgeStore:
    """Local source-backed knowledge store with lightweight retrieval."""

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or KNOWLEDGE_PATH)
        self.root.mkdir(parents=True, exist_ok=True)

    def add(self, document: KnowledgeDocument) -> Path:
        filename = self._safe_filename(document.title) + ".txt"
        path = self.root / filename
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        if existing and document.content.strip() in self._body(existing):
            return path
        added_at = datetime.now(timezone.utc).isoformat()
        header = (f"Source: {document.source}\nTitle: {document.title}\n"
                  f"Type: {document.document_type}\nAdded: {added_at}\n\n")
        path.write_text(header + document.content.strip() + "\n", encoding="utf-8")
        return path

    def list_documents(self) -> list[Path]:
        return sorted(self.root.glob("*.txt"))

    def find_duplicate_content(self, content: str) -> list[Path]:
        normalized = " ".join(content.split()).lower()
        if not normalized:
            return []
        return [p for p in self.list_documents()
                if normalized == " ".join(self._body(self.read(p)).split()).lower()]

    def read(self, path: str | Path) -> str:
        return Path(path).read_text(encoding="utf-8")

    def get_excerpt(self, path: str | Path, max_chars: int = 1200) -> str:
        return self._body(self.read(path))[:max_chars]

    def get_metadata(self, path: str | Path) -> dict[str, str]:
        return self._parse_metadata(self.read(path))

    def chunk_document(self, path, max_chars=800, overlap=100) -> list[KnowledgeChunk]:
        return split_text(self._body(self.read(path)), max_chars, overlap)

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {t for t in re.findall(r"[\w%]+", value.lower()) if len(t) > 2}

    def search(self, query: str, limit: int = 3):
        terms = self._terms(query)
        if not terms:
            return []
        scored = []
        for path in self.list_documents():
            text = self._body(self.read(path)).lower()
            score = sum(text.count(term) for term in terms)
            if score:
                scored.append((path, score))
        scored.sort(key=lambda x: (-x[1], x[0].name.lower()))
        return scored[:limit]

    def search_chunks(self, query, limit=3, max_chars=800, overlap=100):
        terms = self._terms(query)
        if not terms:
            return []
        scored = []
        for path in self.list_documents():
            metadata = self.get_metadata(path)
            for chunk in self.chunk_document(path, max_chars, overlap):
                text = chunk.text.lower()
                matched = sum(1 for term in terms if term in text)
                if not matched:
                    continue
                frequency = sum(text.count(term) for term in terms)
                coverage = matched / len(terms)
                bonus = {"curated_basics": 1.5, "manual": 0.5,
                         "file": 0.25}.get(metadata.get("source", ""), 0)
                score = coverage * 5 + min(frequency, 4) + bonus
                if query.strip().lower() in text:
                    score += 2
                scored.append((path, chunk, score))
        scored.sort(key=lambda x: (-x[2], x[0].name.lower(), x[1].index))
        return scored[:limit]

    def search_with_metadata(self, query, limit=3):
        return [(p, s, self.get_metadata(p)) for p, s in self.search(query, limit)]

    @staticmethod
    def _body(text):
        parts = text.split("\n\n", 1)
        return parts[1].strip() if len(parts) == 2 else text.strip()

    @staticmethod
    def _parse_metadata(text):
        metadata = {}
        for line in text.splitlines():
            if not line.strip():
                break
            key, sep, value = line.partition(":")
            if sep:
                metadata[key.strip().lower()] = value.strip()
        return metadata

    @staticmethod
    def _safe_filename(value):
        cleaned = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in value)
        return "_".join(cleaned.split()) or "document"
