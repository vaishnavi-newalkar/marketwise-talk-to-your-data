def build_context(chat_history, max_turns=3):
    """
    Builds relevant conversational context for the current query.

    Args:
        chat_history (list): List of dicts with keys:
            - "role": "user" | "system"
            - "content": str
        max_turns (int): Number of recent turns to include

    Returns:
        str: Context text to prepend to LLM prompt
    """

    if not chat_history:
        return ""

    # Take last N turns (user + system)
    recent_history = chat_history[-max_turns * 2:]

    context_lines = []
    for msg in recent_history:
        role = msg.get("role", "user")
        content = msg.get("content", "")

        if not content:
            continue

        prefix = "User" if role == "user" else "System"
        context_lines.append(f"{prefix}: {content}")

    return "\n".join(context_lines)
