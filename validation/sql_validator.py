import re


class SQLValidationError(Exception):
    """Raised when SQL validation fails."""
    pass


FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete",
    "drop", "alter", "truncate",
    "create", "attach", "detach",
    "replace", "reindex", "vacuum"
}


def validate_sql(sql: str) -> bool:
    """
    Validates SQL for safety.

    Rules:
    - READ-ONLY queries only
    - Single statement
    - No comments
    - No destructive or schema-altering keywords
    """

    if not sql or not sql.strip():
        raise SQLValidationError("Empty SQL query.")

    sql_clean = sql.strip().lower()

    # 1️⃣ Must be read-only
    if not (
        sql_clean.startswith("select")
        or sql_clean.startswith("with")
        or sql_clean.startswith("pragma")
    ):
        raise SQLValidationError("Only READ-ONLY SQL queries are allowed.")

    # 2️⃣ No multiple statements
    if ";" in sql_clean[:-1]:
        raise SQLValidationError("Multiple SQL statements are not allowed.")

    # 3️⃣ Block comments (SQL injection prevention)
    if re.search(r"--|/\*|\*/", sql_clean):
        raise SQLValidationError("SQL comments are not allowed.")

    # 4️⃣ Block forbidden keywords
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_clean):
            raise SQLValidationError(
                f"Forbidden SQL keyword detected: {keyword.upper()}"
            )

    return True
