"""
LLM-Based Answer Generator

Generates human-readable final answers by analyzing:
- The original question
- The SQL query used
- The result rows returned

This provides intelligent, context-aware responses.
"""

from typing import Dict, List, Any, Optional


def generate_final_answer(
    llm_client,
    question: str,
    sql: str,
    columns: List[str],
    rows: List[List[Any]],
    row_count: int
) -> str:
    """
    Uses LLM to generate a human-readable final answer.
    
    Args:
        llm_client: LLM client instance
        question: Original user question
        sql: SQL query that was executed
        columns: Column names from result
        rows: Result rows (limited preview)
        row_count: Total row count
    
    Returns:
        str: Natural language answer
    """
    
    # Format results for LLM
    results_text = _format_results_for_llm(columns, rows, row_count)
    
    prompt = f"""You are a helpful data analyst. Based on the user's question and the query results, provide a clear, natural language answer.

USER QUESTION:
{question}

SQL QUERY EXECUTED:
{sql}

QUERY RESULTS:
{results_text}

TOTAL ROWS RETURNED: {row_count}

INSTRUCTIONS:
1. Provide a direct, conversational answer to the user's question
2. If there are results, summarize the key findings
3. If no results, explain what this means in context
4. Use specific numbers and data from the results
5. Keep the answer concise but informative
6. Use markdown formatting for emphasis (bold for key numbers)
7. If it's a count/total, state it clearly
8. If listing items, mention the top few and total count

YOUR ANSWER:"""
    
    try:
        answer = llm_client.generate(prompt, temperature=0.3)
        return answer.strip()
    except Exception as e:
        # Fallback to basic interpretation
        return _generate_fallback_answer(question, columns, rows, row_count)


def _format_results_for_llm(
    columns: List[str],
    rows: List[List[Any]],
    row_count: int,
    max_rows: int = 10
) -> str:
    """Formats query results as text for LLM consumption."""
    
    if not rows:
        return "No rows returned (empty result set)"
    
    # Limit rows for LLM context
    preview_rows = rows[:max_rows]
    
    lines = []
    
    # Header
    if columns:
        lines.append("| " + " | ".join(str(c) for c in columns) + " |")
        lines.append("|" + "|".join(["---"] * len(columns)) + "|")
    
    # Data rows
    for row in preview_rows:
        formatted_values = []
        for val in row:
            if val is None:
                formatted_values.append("NULL")
            elif isinstance(val, float):
                formatted_values.append(f"{val:.2f}")
            else:
                formatted_values.append(str(val))
        lines.append("| " + " | ".join(formatted_values) + " |")
    
    if row_count > max_rows:
        lines.append(f"\n... and {row_count - max_rows} more rows")
    
    return "\n".join(lines)


def _generate_fallback_answer(
    question: str,
    columns: List[str],
    rows: List[List[Any]],
    row_count: int
) -> str:
    """Generates a basic answer without LLM (fallback)."""
    
    if not rows:
        return "The query returned no results. This could mean the data you're looking for doesn't exist in the database."
    
    if row_count == 1 and len(columns) == 1:
        value = rows[0][0]
        if isinstance(value, (int, float)):
            return f"The result is **{value:,}**."
        return f"The result is **{value}**."
    
    if row_count == 1:
        return f"Found **1 result** matching your query."
    
    return f"Found **{row_count:,} results** matching your query."


def generate_step_by_step_reasoning(
    question: str,
    schema_tables: List[str],
    plan: Dict,
    sql: str
) -> List[Dict[str, str]]:
    """
    Generates step-by-step reasoning for display during loading.
    
    Returns:
        List of steps with 'icon', 'text', and 'status'
    """
    
    steps = []
    
    # Step 1: Understanding the question
    q_lower = question.lower()
    if "how many" in q_lower or "count" in q_lower:
        intent = "count records"
    elif "list" in q_lower or "show" in q_lower:
        intent = "list records"
    elif "total" in q_lower or "sum" in q_lower:
        intent = "calculate total"
    elif "average" in q_lower:
        intent = "calculate average"
    elif "top" in q_lower or "highest" in q_lower:
        intent = "find top values"
    else:
        intent = "retrieve data"
    
    steps.append({
        "icon": "🔍",
        "text": f"Understanding query intent: {intent}",
        "status": "complete"
    })
    
    # Step 2: Schema analysis
    steps.append({
        "icon": "📊",
        "text": f"Checking schema... found {', '.join(schema_tables[:3])}{'...' if len(schema_tables) > 3 else ''} table(s)",
        "status": "complete"
    })
    
    # Step 3: Relationship detection
    if plan.get("needs_join"):
        steps.append({
            "icon": "🔗",
            "text": "Detected relationship between tables - JOIN required",
            "status": "complete"
        })
    
    # Step 4: Pattern detection
    if plan.get("aggregation"):
        steps.append({
            "icon": "📈",
            "text": f"Aggregation needed: {plan['aggregation']}",
            "status": "complete"
        })
    
    if plan.get("negation"):
        steps.append({
            "icon": "❌",
            "text": "Negation pattern detected - using LEFT JOIN with NULL check",
            "status": "complete"
        })
    
    if plan.get("intersection"):
        steps.append({
            "icon": "∩",
            "text": "Multiple conditions - using INTERSECT or GROUP BY HAVING",
            "status": "complete"
        })
    
    # Step 5: Strategy
    complexity = plan.get("complexity", "simple")
    strategy_map = {
        "simple": "Direct SELECT query",
        "moderate": "JOIN with aggregation",
        "complex": "Subquery or CTE approach",
        "multi_step": "Multi-step CTE strategy"
    }
    
    steps.append({
        "icon": "🎯",
        "text": f"Strategy: {strategy_map.get(complexity, 'Direct query')}",
        "status": "complete"
    })
    
    # Step 6: Generating query
    steps.append({
        "icon": "⚙️",
        "text": "Generating optimized SQL query...",
        "status": "complete"
    })
    
    return steps
