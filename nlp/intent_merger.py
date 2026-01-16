def merge_intent(
    original_query: str,
    clarification_response: str,
    clarification_state: dict
) -> str:
    """
    Merges user clarification response into the original ambiguous query.

    Args:
        original_query (str): The original user query (ambiguous)
        clarification_response (str): User's clarification answer
        clarification_state (dict): Contains:
            - term: ambiguous word
            - options: list of possible meanings

    Returns:
        str: Updated, clarified query
    """

    term = clarification_state.get("term")
    options = clarification_state.get("options", [])

    response_lower = clarification_response.lower()

    # Try to match clarification response with known options
    selected_option = None
    for opt in options:
        if any(word in response_lower for word in opt.lower().split()):
            selected_option = opt
            break

    # Fallback: use raw clarification response
    if not selected_option:
        selected_option = clarification_response.strip()

    # Replace ambiguous term with clarified intent
    clarified_query = original_query.lower().replace(
        term,
        f"{term} by {selected_option}"
    )

    return clarified_query
