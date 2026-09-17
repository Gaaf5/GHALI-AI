from app.knowledge.manager import KnowledgeManager
from app.knowledge.store import KnowledgeStore
from app.memory import MemoryManager


def test_knowledge_inventory_valid():
    store = KnowledgeStore()
    manager = KnowledgeManager(store)
    assert len(manager.inventory()) >= 1
    assert manager.validate() == []


def test_memory_dedup_and_delete():
    memory = MemoryManager()
    before = memory.count()
    first = memory.remember("TEST durable memory", "general", 1)
    second = memory.remember("TEST durable memory", "general", 5)
    assert first == second
    assert memory.count() == before + 1
    memory.forget(first)
    assert memory.count() == before
    memory.close()
