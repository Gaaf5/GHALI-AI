from app.brain.brain import Brain
from app.knowledge.store import KnowledgeStore
from app.llm.base import BaseLLM
from app.memory import MemoryManager


class DummyLLM(BaseLLM):
    def chat(self, messages):
        tool_text = messages[0]["content"]
        assert "DETERMINISTIC TOOL RESULT" in tool_text
        return "TOOL_OK"


def test_mass_percent_tool_executes():
    memory = MemoryManager()
    brain = Brain(DummyLLM(), KnowledgeStore(), memory)
    answer = brain.think("calculate mass percent 5 g in 100 g")
    assert answer.startswith("TOOL_OK")
    assert "Sources:" in answer
    memory.close()
