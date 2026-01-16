class ConversationMemory:
    """
    Manages conversational memory for a session.
    """

    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history = []  # list of {role, content}

    def add_user_message(self, content: str):
        self._add_message("user", content)

    def add_system_message(self, content: str):
        self._add_message("system", content)

    def _add_message(self, role: str, content: str):
        if not content:
            return

        self.history.append({
            "role": role,
            "content": content
        })

        # Sliding window: keep last N turns
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-self.max_turns * 2:]

    def get_history(self):
        return self.history

    def clear(self):
        self.history = []
