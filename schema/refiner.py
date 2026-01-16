from schema.fk_graph import FKGraph


def refine_schema(
    full_schema: dict,
    user_query: str,
    top_k: int = 3,
    fk_hops: int = 1
) -> dict:
    """
    Dynamically selects the most relevant subset of the schema.

    Args:
        full_schema (dict): Cached full schema
        user_query (str): User question
        top_k (int): Number of seed tables
        fk_hops (int): FK graph expansion depth

    Returns:
        dict: Refined schema
    """

    keywords = user_query.lower().split()
    table_scores = []

    for table, info in full_schema.items():
        score = 0

        # Table name match (high weight)
        if table.lower() in keywords:
            score += 3

        # Column name matches
        for col in info.get("columns", []):
            if col.lower() in keywords:
                score += 1

        if score > 0:
            table_scores.append((table, score))

    # Fallback: if nothing matched, pick first few tables
    if not table_scores:
        seed_tables = list(full_schema.keys())[:top_k]
    else:
        table_scores.sort(key=lambda x: x[1], reverse=True)
        seed_tables = [t for t, _ in table_scores[:top_k]]

    # Expand via foreign keys
    fk_graph = FKGraph(full_schema)
    expanded_tables = fk_graph.expand_tables(seed_tables, hops=fk_hops)

    # Column pruning: keep only relevant columns
    refined_schema = {}
    for table in expanded_tables:
        info = full_schema[table]
        cols = info.get("columns", [])

        relevant_cols = [
            col for col in cols
            if col.lower() in keywords or table in seed_tables
        ]

        # Fallback: keep all columns if pruning removes everything
        if not relevant_cols:
            relevant_cols = cols

        refined_schema[table] = {
            **info,
            "columns": relevant_cols
        }

    return refined_schema
