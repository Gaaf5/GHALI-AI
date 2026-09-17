from .memory_store import MemoryStore


class MemoryManager:
    ALLOWED_CATEGORIES = {
        "user", "project", "preference", "rule",
        "fact", "task", "general",
    }

    def __init__(self, store=None):
        self.store = store or MemoryStore()

    def remember(self, content, category="general", importance=1):
        content = content.strip()
        category = category.lower().strip()
        if not content:
            raise ValueError("Memory content cannot be empty")
        if category not in self.ALLOWED_CATEGORIES:
            raise ValueError(f"Invalid memory category: {category}")
        importance = max(1, min(int(importance), 5))
        existing = self.store.find_similar(content, category)
        if existing:
            return existing[0][0]
        return self.store.add(content, category, importance)

    def recall(self, query, limit=5):
        return self.store.search(query, limit)

    def inventory(self, limit=50):
        return self.store.list(limit)

    def forget(self, memory_id):
        self.store.delete(memory_id)

    def count(self):
        return self.store.count()

    def close(self):
        self.store.close()


class MemoryCLI:
    def __init__(self, memory):
        self.memory = memory

    def _format(self, rows):
        if not rows:
            return "No memories."
        return "\n".join(
            f"{row[0]} | {row[1]} | importance={row[3]} | {row[2]}"
            for row in rows
        )

    def run_command(self, command, *args):
        command = command.lower()
        if command == "list":
            return self._format(self.memory.inventory())
        if command == "search":
            return self._format(self.memory.recall(" ".join(args).strip()))
        if command == "add":
            if not args:
                return "Usage: add <content> [category] [importance]"
            category = "general"
            importance = 2
            content_parts = list(args)
            if len(content_parts) >= 1 and content_parts[-1].isdigit():
                importance = int(content_parts.pop())
            if content_parts and content_parts[-1].lower() in self.memory.ALLOWED_CATEGORIES:
                category = content_parts.pop().lower()
            if not content_parts:
                return "Usage: add <content> [category] [importance]"
            memory_id = self.memory.remember(
                " ".join(content_parts), category, importance
            )
            return f"Memory saved: {memory_id}"
        if command in {"delete", "remove"}:
            if not args:
                return "Usage: delete <id>"
            self.memory.forget(int(args[0]))
            return f"Memory deleted: {args[0]}"
        if command == "count":
            return f"Memory count: {self.memory.count()}"
        if command == "help":
            return (
                "Commands: list | search <query> | "
                "add <content> [category] [importance] | delete <id> | count"
            )
        return f"Unknown memory command: {command}"
