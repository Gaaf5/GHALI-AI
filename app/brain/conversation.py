class Conversation:
    def __init__(self, max_messages=12):
        self.max_messages = max_messages
        self.messages = []

    def add_user(self, text):
        self.messages.append({
            "role": "user",
            "content": text,
        })
        self._trim()

    def add_assistant(self, text):
        self.messages.append({
            "role": "assistant",
            "content": text,
        })
        self._trim()

    def get_messages(self):
        return list(self.messages)

    def clear(self):
        self.messages.clear()

    def _trim(self):
        if len(self.messages) > self.max_messages:
            self.messages = self.messages[-self.max_messages:]
