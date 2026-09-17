from .ingest import ingest_file
from .manager import KnowledgeManager
from .store import KnowledgeStore


class KnowledgeCLI:
    def __init__(self, store=None):
        self.store = store or KnowledgeStore()
        self.manager = KnowledgeManager(self.store)

    def run_command(self, command: str, *args: str) -> str:
        normalized = command.strip().lower()
        if normalized == "list":
            items = self.manager.inventory()
            if not items:
                return "No knowledge documents."
            return "\n".join(
                f"{item['title']} | {item['type']} | {item['source']}"
                for item in items
            )

        if normalized == "validate":
            issues = self.manager.validate()
            return "Knowledge OK." if not issues else "\n".join(issues)

        if normalized == "search":
            query = " ".join(args).strip()
            if not query:
                return "Usage: search <query>"
            results = self.manager.find(query, limit=5)
            if not results:
                return "No matching knowledge found."
            return "\n".join(
                f"{path.name} | chunk={chunk.index} | score={score}"
                for path, chunk, score in results
            )

        if normalized == "details":
            if not args:
                return "Usage: details <filename>"
            item = self.manager.details(args[0])
            if not item:
                return "Document not found."
            return "\n".join(f"{key}: {value}" for key, value in item.items())

        if normalized == "remove":
            if not args:
                return "Usage: remove <filename>"
            return "Removed." if self.manager.remove(args[0]) else "Document not found."

        if normalized == "ingest":
            if not args:
                return "Usage: ingest <path> [source]"
            path = args[0]
            source = args[1] if len(args) > 1 else "file"
            stored = ingest_file(path, self.store, source=source)
            return f"Ingested: {stored.name}"

        if normalized == "help":
            return (
                "Knowledge commands: list | validate | search <query> | "
                "details <filename> | remove <filename> | "
                "ingest <path> [source] | help | back"
            )

        return f"Unknown knowledge command: {command}"
