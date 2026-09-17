from .manager import MemoryManager


class AutoMemory:
    """Conservative automatic memory capture for durable statements."""

    CATEGORY_HINTS = {
        "user": ("my name is ", "i am ", "i'm "),
        "preference": ("i prefer ", "i like ", "i don't like ", "i want "),
        "project": ("ghali ai", "this project", "our project"),
        "rule": ("always ", "never ", "do not ", "don't "),
        "task": ("we need to ", "remember to ", "todo "),
    }

    def __init__(self, memory: MemoryManager):
        self.memory = memory

    def capture(self, text):
        clean = " ".join(text.strip().split())
        lower = clean.lower()
        if len(clean) < 12:
            return None

        for category, hints in self.CATEGORY_HINTS.items():
            if any(lower.startswith(hint) or f" {hint}" in lower for hint in hints):
                importance = 4 if category in {"project", "rule"} else 3
                memory_id = self.memory.remember(clean, category, importance)
                return memory_id, category
        return None
