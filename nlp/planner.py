def create_plan(question: str, schema: dict) -> dict:
    """
    Creates a structured reasoning plan for SQL generation.
    This plan is:
    - LLM-friendly
    - UI-explainable
    - Safe to expose to users
    """

    q = question.lower()
    tables = list(schema.keys())

    plan = {
        "intent": "select",
        "tables_considered": tables,
        "needs_join": len(tables) > 1,
        "filters_detected": False,
        "aggregation": None,
        "sorting": None,
        "limit": None,
        "reasoning_summary": []
    }

    # Detect filters
    filter_keywords = ["where", "after", "before", "in", "on", "from", "year", "date", "more than", "less than"]
    if any(k in q for k in filter_keywords):
        plan["filters_detected"] = True
        plan["reasoning_summary"].append(
            "The question includes conditions that restrict the result set."
        )

    # Detect aggregation
    aggregation_map = {
        "count": "COUNT",
        "sum": "SUM",
        "total": "SUM",
        "average": "AVG",
        "avg": "AVG",
        "max": "MAX",
        "min": "MIN"
    }

    for k, agg in aggregation_map.items():
        if k in q:
            plan["aggregation"] = agg
            plan["intent"] = "aggregation"
            plan["reasoning_summary"].append(
                f"The question asks for a {agg.lower()} calculation."
            )
            break

    # Detect ranking / sorting
    if any(k in q for k in ["top", "highest", "lowest", "most", "least"]):
        plan["sorting"] = "DESC"
        plan["limit"] = 10
        plan["reasoning_summary"].append(
            "The results need to be ranked to identify top or bottom values."
        )

    # Base reasoning
    plan["reasoning_summary"].insert(
        0,
        "Relevant tables are selected based on the entities mentioned in the conversation."
    )

    return plan
