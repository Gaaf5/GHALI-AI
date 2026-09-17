from abc import ABC, abstractmethod


class BaseLLM(ABC):

    @abstractmethod
    def chat(self, messages):
        """Send messages to the language model."""
        pass