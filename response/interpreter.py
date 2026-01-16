"""
Result Interpreter

Converts SQL execution results to natural language.
Generates human-readable explanations with context-aware messaging.
"""

from typing import Dict, List, Any, Optional


def interpret(result: Dict, question: str = "", max_preview_rows: int = 100) -> Dict:
    """
    Interprets SQL execution results into a human-readable response.
    
    Args:
        result: Dict from executor with columns, rows, row_count, truncated
        question: Original user question for context
        max_preview_rows: Max rows for table display
    
    Returns:
        dict with answer, summary, preview_rows, columns, total_count
    """
    
    columns = result.get("columns", [])
    rows = result.get("rows", [])
    row_count = result.get("row_count", 0)
    truncated = result.get("truncated", False)
    
    # Empty result
    if not rows:
        answer = _generate_empty_answer(question, columns)
        return {
            "answer": answer,
            "summary": "The query returned no matching records.",
            "preview_rows": [],
            "columns": columns,
            "total_count": 0
        }
    
    # Single scalar result (COUNT, SUM, AVG, etc.)
    if row_count == 1 and len(columns) == 1:
        value = rows[0][0]
        col_name = columns[0]
        
        answer = _format_scalar_answer(value, col_name, question)
        
        return {
            "answer": answer,
            "summary": f"Calculated: {col_name} = {value}",
            "preview_rows": rows,
            "columns": columns,
            "total_count": 1
        }
    
    # Single row with multiple columns
    if row_count == 1 and len(columns) > 1:
        row = rows[0]
        
        # Format as a nice description
        details = []
        for col, val in zip(columns, row):
            formatted_col = _format_column_name(col)
            formatted_val = _format_value(val)
            details.append(f"**{formatted_col}**: {formatted_val}")
        
        answer = "Found **1 result**:\n\n" + "  \n".join(details)
        
        return {
            "answer": answer,
            "summary": "Single record found.",
            "preview_rows": rows,
            "columns": columns,
            "total_count": 1
        }
    
    # Multiple rows - provide summary
    preview_rows = rows[:max_preview_rows]
    
    # Generate contextual summary
    answer = _generate_multi_row_answer(
        row_count=row_count,
        columns=columns,
        rows=rows[:5],  # Use first 5 for summary
        question=question,
        truncated=truncated
    )
    
    summary = f"Found {row_count} records."
    if truncated:
        summary += " (Results truncated)"
    
    return {
        "answer": answer,
        "summary": summary,
        "preview_rows": preview_rows,
        "columns": columns,
        "total_count": row_count
    }


def _generate_empty_answer(question: str, columns: List[str]) -> str:
    """Generates a meaningful message for empty results."""
    
    q = question.lower()
    
    # Questions about non-existence
    if any(phrase in q for phrase in ["never", "without", "haven't", "haven't", "hasn't", "no "]):
        return ("**No matching records found.** This means all records in the database "
                "satisfy the opposite condition of what you asked about.")
    
    # Questions about existence
    if any(phrase in q for phrase in ["are there", "is there", "does", "do any", "exist"]):
        return "**No** - there are no records matching your criteria in the database."
    
    # Who/which questions
    if any(phrase in q for phrase in ["who", "which", "what"]):
        return ("**No records found** matching your criteria. "
                "The data you're looking for may not exist in the database.")
    
    # Default
    return "The query executed successfully but **returned no results**."


def _format_scalar_answer(value: Any, col_name: str, question: str) -> str:
    """Formats a single scalar value with context."""
    
    if value is None:
        return "The result is **NULL** (no value found)."
    
    col_lower = col_name.lower()
    q_lower = question.lower()
    
    # Format number with commas
    if isinstance(value, (int, float)):
        if isinstance(value, float):
            formatted = f"{value:,.2f}"
        else:
            formatted = f"{value:,}"
    else:
        formatted = str(value)
    
    # Detect aggregation type
    if "count" in col_lower or "count" in q_lower or "how many" in q_lower:
        if value == 0:
            return "The count is **0** - no matching records found."
        elif value == 1:
            return f"There is **{formatted}** matching record."
        else:
            return f"There are **{formatted}** matching records."
    
    if "sum" in col_lower or "total" in col_lower or "total" in q_lower:
        return f"The total is **{formatted}**."
    
    if "avg" in col_lower or "average" in col_lower or "average" in q_lower:
        return f"The average is **{formatted}**."
    
    if "min" in col_lower or "minimum" in q_lower or "lowest" in q_lower:
        return f"The minimum value is **{formatted}**."
    
    if "max" in col_lower or "maximum" in q_lower or "highest" in q_lower:
        return f"The maximum value is **{formatted}**."
    
    # Revenue/sales specific
    if any(term in col_lower or term in q_lower for term in ["revenue", "sales", "amount", "price"]):
        return f"The result is **${formatted}**."
    
    return f"The result is **{formatted}**."


def _format_column_name(col: str) -> str:
    """Formats column name for display."""
    # Convert snake_case or CamelCase to readable
    import re
    
    # Handle snake_case
    formatted = col.replace("_", " ")
    
    # Handle CamelCase
    formatted = re.sub(r'([a-z])([A-Z])', r'\1 \2', formatted)
    
    return formatted.title()


def _format_value(value: Any) -> str:
    """Formats a value for display."""
    
    if value is None:
        return "*N/A*"
    
    if isinstance(value, bool):
        return "Yes" if value else "No"
    
    if isinstance(value, float):
        return f"{value:,.2f}"
    
    if isinstance(value, int):
        return f"{value:,}"
    
    return str(value)


def _generate_multi_row_answer(
    row_count: int,
    columns: List[str],
    rows: List[List[Any]],
    question: str,
    truncated: bool
) -> str:
    """Generates a summary answer for multiple rows."""
    
    q = question.lower()
    
    # Start with count
    if row_count == 1:
        answer = "Found **1 result**."
    else:
        answer = f"Found **{row_count:,} results**."
    
    # Add context based on question type
    if "top" in q or "best" in q or "highest" in q:
        if rows and len(columns) >= 2:
            top_item = rows[0]
            # Try to identify the name column (usually first or second)
            name_idx = 0
            for i, col in enumerate(columns):
                if any(term in col.lower() for term in ["name", "title", "artist", "customer"]):
                    name_idx = i
                    break
            
            if name_idx < len(top_item):
                answer += f" The top result is **{top_item[name_idx]}**."
    
    elif "least" in q or "lowest" in q or "worst" in q:
        if rows and len(columns) >= 2:
            bottom_item = rows[0]
            name_idx = 0
            for i, col in enumerate(columns):
                if any(term in col.lower() for term in ["name", "title", "artist", "customer"]):
                    name_idx = i
                    break
            
            if name_idx < len(bottom_item):
                answer += f" The lowest is **{bottom_item[name_idx]}**."
    
    # Add truncation notice
    if truncated:
        answer += " *(Results were truncated)*"
    
    return answer


# Backward compatibility
def interpret_simple(rows: list, max_preview_rows: int = 5) -> str:
    """Legacy interpreter for raw rows."""
    if not rows:
        return "No results found for the given query."
    
    if len(rows) == 1 and len(rows[0]) == 1:
        return f"The result is {rows[0][0]}."
    
    if len(rows) <= max_preview_rows:
        preview = "\n".join(str(row) for row in rows)
        return f"Here are the results:\n{preview}"
    
    preview = "\n".join(str(row) for row in rows[:max_preview_rows])
    return f"Returned {len(rows)} rows.\nShowing first {max_preview_rows}:\n{preview}"
