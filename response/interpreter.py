def interpret(rows, max_preview_rows=5):
    """
    Interprets raw SQL result rows into a human-readable response.

    Args:
        rows (list[tuple]): SQL query result
        max_preview_rows (int): Max rows to preview

    Returns:
        str: Natural language explanation
    """

    if not rows:
        return "No results found for the given query."

    # Case 1: Single scalar result (COUNT, SUM, AVG, etc.)
    if len(rows) == 1 and len(rows[0]) == 1:
        return f"The result is {rows[0][0]}."

    # Case 2: Small result set
    if len(rows) <= max_preview_rows:
        preview = "\n".join(str(row) for row in rows)
        return f"Here are the results:\n{preview}"

    # Case 3: Large result set
    preview = "\n".join(str(row) for row in rows[:max_preview_rows])
    return (
        f"Returned {len(rows)} rows.\n"
        f"Showing first {max_preview_rows} rows:\n{preview}"
    )
