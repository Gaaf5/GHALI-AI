from app.brain.brain import Brain
from app.knowledge.store import KnowledgeStore
from app.memory import MemoryManager
from app.llm.base import BaseLLM


class DummyLLM(BaseLLM):
    def chat(self, messages):
        return "OK"


memory = MemoryManager()
brain = Brain(DummyLLM(), KnowledgeStore(), memory)
print(brain._try_tool("mass_percent", "calculate mass percent 5 g in 100 g"))
memory.close()
