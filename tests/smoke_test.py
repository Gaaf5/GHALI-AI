import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.tools import molar_mass, mass_to_moles, mass_percent
from app.knowledge.store import KnowledgeStore
from app.memory import MemoryManager


def main():
    assert round(molar_mass("CH4N2O"), 3) == 60.056
    assert round(mass_to_moles(60.056, "CH4N2O"), 3) == 1.0
    assert mass_percent(25, 100) == 25.0

    knowledge = KnowledgeStore()
    assert len(knowledge.list_documents()) >= 1
    assert not __import__("app.knowledge.manager", fromlist=["KnowledgeManager"]).KnowledgeManager(knowledge).validate()

    memory = MemoryManager()
    before = memory.count()
    memory_id = memory.remember("Smoke test durable memory", "general", 1)
    assert memory.store.get(memory_id)[2] == "Smoke test durable memory"
    memory.forget(memory_id)
    assert memory.count() == before
    memory.close()
    print("SMOKE TEST OK")


if __name__ == "__main__":
    main()
