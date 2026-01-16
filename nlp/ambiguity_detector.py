AMBIGUOUS_PATTERNS = {
    "top": ["highest value", "most frequent", "most recent"],
    "best": ["highest rating", "highest revenue", "most popular"],
    "highest": ["maximum value", "maximum count"],
    "latest": ["most recent date", "last inserted record"]
}


def detect_ambiguity(query: str):
    """
    Detects ambiguity in a user query.

    Returns:
        (bool, dict | None)
        If ambiguous:
            True, {
                "term": str,
                "options": list[str],
                "question": str
            }
        Else:
            False, None
    """

    query_lower = query.lower()

    for term, options in AMBIGUOUS_PATTERNS.items():
        if term in query_lower:
            clarification_question = (
                f"When you say '{term}', what do you mean? "
                f"({', '.join(options)})"
            )

            return True, {
                "term": term,
                "options": options,
                "question": clarification_question
            }

    return False, None
