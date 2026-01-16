from session.memory import ConversationMemory


class Session:
    """
    Represents a single user session bound to one database.
    """

    def __init__(self, db_path: str, schema: dict):
        self.db_path = db_path
        self.full_schema = schema

        # Managed conversation memory
        self.memory = ConversationMemory(max_turns=10)

        # Holds ambiguity clarification state (if any)
        self.clarification_state = None

    def add_user_message(self, message: str):
        self.memory.add_user_message(message)

    def add_system_message(self, message: str):
        self.memory.add_system_message(message)

    def get_chat_history(self):
        return self.memory.get_history()

    def clear_clarification(self):
        self.clarification_state = None
