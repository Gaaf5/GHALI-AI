from dataclasses import dataclass
from .manager import MemoryManager

@dataclass
class LearningResult:
    saved: bool
    category: str = ""
    memory_id: int | None = None
    candidate_id: int | None = None
    reason: str = ""

class ContinuousLearner:
    """Conservative learning layer for durable user/project knowledge."""
    HIGH_CONFIDENCE = (
        "my name is ", "i prefer ", "i don't like ", "i always ", "i never ",
        "remember that ", "from now on ", "our factory ", "our plant ",
        "in our factory ", "in our plant ", "in our line ", "we use ", "we have ",
    )
    CATEGORY_HINTS = {
        "preference": ("i prefer ", "i like ", "i don't like ", "i want "),
        "rule": ("i always ", "i never ", "from now on ", "remember that "),
        "project": ("ghali ai", "our project"),
        "fact": ("our factory ", "our plant ", "in our factory ", "in our plant ", "in our line ", "we use ", "we have "),
        "user": ("my name is ",),
    }
    def __init__(self, memory: MemoryManager):
        self.memory = memory
    def classify(self, text):
        low=" ".join(text.strip().split()).lower()
        for cat,hints in self.CATEGORY_HINTS.items():
            if any(h in low for h in hints):
                return cat
        return "general"
    def learn(self, text):
        clean=" ".join(text.strip().split())
        low=clean.lower()
        if len(clean)<12:
            return LearningResult(False,reason="too_short")
        cat=self.classify(clean)
        if cat=="general":
            return LearningResult(False,reason="no_durable_signal")
        if any(h in low for h in self.HIGH_CONFIDENCE):
            mid=self.memory.remember(clean,cat,4)
            return LearningResult(True,cat,mid,reason="explicit_durable_statement")
        cid=self.memory.store.add_candidate(clean,cat,2,.55,"conversation")
        return LearningResult(False,cat,candidate_id=cid,reason="candidate")
