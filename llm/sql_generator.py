"""
Enhanced SQL Generator with Reasoning Support.

Handles all complexity levels:
- Simple queries (single table, basic conditions)
- Moderate queries (JOINs, aggregations)
- Complex queries (subqueries, CTEs, multi-step logic)
- Multi-step reasoning (customers who purchased from both X and Y)
"""

import re
from typing import Dict, Tuple, Optional


class SQLGenerationError(Exception):
    """Raised when SQL generation or parsing fails."""
    pass


def generate_sql_with_reasoning(
    llm_client,
    plan: Dict,
    schema: Dict,
    question: str,
    retry_context: str = ""
) -> Dict:
    """
    Generates SQL query with detailed reasoning.
    
    Args:
        llm_client: LLM client instance
        plan: Query plan from planner
        schema: Refined database schema
        question: User's question with context
        retry_context: Optional context from previous failed attempts
    
    Returns:
        dict with 'sql', 'reasoning', 'plan_summary'
    
    Raises:
        SQLGenerationError: If output format is invalid
    """
    
    schema_text = format_schema_for_prompt(schema)
    plan_text = format_plan_for_prompt(plan)
    
    # Detect query complexity for appropriate prompting
    complexity = detect_query_complexity(question, plan)
    
    prompt = _build_prompt(
        schema_text=schema_text,
        plan_text=plan_text,
        question=question,
        complexity=complexity,
        retry_context=retry_context
    )
    
    raw_response = llm_client.generate(prompt, temperature=0.1)
    
    result = parse_llm_response(raw_response)
    result["plan_summary"] = plan_text
    result["complexity"] = complexity
    
    return result


def _build_prompt(
    schema_text: str,
    plan_text: str,
    question: str,
    complexity: str,
    retry_context: str = ""
) -> str:
    """Builds the LLM prompt based on query complexity."""
    
    # Complexity-specific instructions
    complexity_instructions = {
        "simple": """
For this simple query:
- Use a single SELECT statement
- Apply basic WHERE conditions
- Keep the query straightforward
""",
        "moderate": """
For this moderate query:
- Use JOINs to connect related tables
- Apply aggregations (COUNT, SUM, AVG) with GROUP BY
- Use proper aliasing for clarity
- Consider using ORDER BY and LIMIT
""",
        "complex": """
For this complex query:
- Consider using subqueries or CTEs (WITH clause) for multi-step logic
- For "both X and Y" conditions, use INTERSECT or GROUP BY HAVING COUNT
- For "never/without" conditions, use LEFT JOIN with NULL check or NOT EXISTS
- Break down the problem step by step in your reasoning
- Ensure proper handling of NULLs
""",
        "multi_step": """
For this multi-step query:
- Use CTEs (WITH clause) to break down the logic
- First CTE: identify the first condition
- Second CTE: identify the second condition
- Final SELECT: combine or filter based on both
- Example pattern for "customers who purchased both X and Y":
  WITH purchased_x AS (...), purchased_y AS (...)
  SELECT DISTINCT customer_id FROM purchased_x
  INTERSECT
  SELECT DISTINCT customer_id FROM purchased_y
"""
    }
    
    complexity_guide = complexity_instructions.get(
        complexity, 
        complexity_instructions["moderate"]
    )
    
    retry_section = ""
    if retry_context:
        retry_section = f"""
═══════════════════════════════════════════════════════════════════
                     PREVIOUS ATTEMPT (FAILED)
═══════════════════════════════════════════════════════════════════
{retry_context}

IMPORTANT: Avoid the same mistakes. Use a different approach.
"""

    return f"""You are a senior SQL expert and data analyst.

Your task is to convert natural language questions into optimized SQLite SQL queries.

═══════════════════════════════════════════════════════════════════
                         CRITICAL RULES
═══════════════════════════════════════════════════════════════════

1. OUTPUT FORMAT (MANDATORY):
   You MUST provide your response in EXACTLY this format:
   
   REASONING:
   <Step-by-step explanation of your approach>
   <Why you chose specific tables, joins, conditions>
   <How you handle edge cases>
   
   SQL:
   <Your SQLite query - NO markdown, NO comments>
   
   ⚠️ BOTH SECTIONS ARE REQUIRED

2. SQL RULES:
   - Generate ONLY valid SQLite SQL
   - Use SELECT or WITH...SELECT only
   - NEVER use INSERT, UPDATE, DELETE, DROP
   - NO SQL comments or markdown code fences
   - Use proper table aliases (e.g., c for Customer)
   - Always qualify column names in JOINs
   - Use LIMIT for "top N" queries

3. COMMON PATTERNS:
   - "How many X" → SELECT COUNT(*)
   - "Top N by Y" → ORDER BY Y DESC LIMIT N  
   - "Total/sum of X" → SELECT SUM(X)
   - "Average X" → SELECT AVG(X)
   - "X who did Y and Z" → Use INTERSECT or GROUP BY HAVING
   - "X who never Y" → LEFT JOIN ... WHERE id IS NULL
   - "Both X and Y" → INTERSECT or GROUP BY HAVING COUNT(DISTINCT) = 2

{complexity_guide}
{retry_section}
═══════════════════════════════════════════════════════════════════
                       DATABASE SCHEMA
═══════════════════════════════════════════════════════════════════
{schema_text}

═══════════════════════════════════════════════════════════════════
                        QUERY PLAN
═══════════════════════════════════════════════════════════════════
{plan_text}

═══════════════════════════════════════════════════════════════════
                      USER QUESTION
═══════════════════════════════════════════════════════════════════
{question}

═══════════════════════════════════════════════════════════════════
                      YOUR RESPONSE
═══════════════════════════════════════════════════════════════════
REASONING:
"""


def detect_query_complexity(question: str, plan: Dict) -> str:
    """
    Detects the complexity level of the query.
    
    Returns: 'simple', 'moderate', 'complex', or 'multi_step'
    """
    
    q = question.lower()
    
    # Multi-step patterns
    multi_step_patterns = [
        r"both .+ and .+",
        r"purchased .+ and .+",
        r"bought .+ and .+",
        r"who .+ and also .+",
        r"that have .+ and .+",
        r".+ as well as .+",
    ]
    
    for pattern in multi_step_patterns:
        if re.search(pattern, q):
            return "multi_step"
    
    # Complex patterns
    complex_patterns = [
        r"\bnever\b",
        r"\bwithout\b",
        r"\bnot have\b",
        r"\bhasn't\b",
        r"\bhaven't\b",
        r"\bno purchase",
        r"\bno order",
        r"\bno sale",
        r"\bdoes not exist",
        r"\bexcept\b",
        r"\bexclude\b",
    ]
    
    for pattern in complex_patterns:
        if re.search(pattern, q):
            return "complex"
    
    # Moderate indicators
    needs_join = plan.get("needs_join", False)
    has_aggregation = plan.get("aggregation") is not None
    has_grouping = plan.get("grouping") is not None
    
    if needs_join or has_aggregation or has_grouping:
        return "moderate"
    
    return "simple"


def format_schema_for_prompt(schema: Dict) -> str:
    """Formats schema dictionary into a readable string for the LLM."""
    
    lines = []
    for table, info in schema.items():
        columns = info.get("columns", [])
        column_types = info.get("column_types", {})
        primary_keys = info.get("primary_key", [])
        fks = info.get("foreign_keys", [])
        
        # Table header
        lines.append(f"Table: {table}")
        
        # Columns with types
        col_parts = []
        for col in columns:
            col_type = column_types.get(col, "")
            pk_marker = " [PK]" if col in primary_keys else ""
            if col_type:
                col_parts.append(f"{col} ({col_type}){pk_marker}")
            else:
                col_parts.append(f"{col}{pk_marker}")
        
        lines.append(f"  Columns: {', '.join(col_parts)}")
        
        # Foreign keys
        if fks:
            fk_strs = []
            for fk in fks:
                if isinstance(fk, dict):
                    fk_strs.append(
                        f"{fk.get('from', '?')} → {fk.get('to_table', '?')}.{fk.get('to_column', '?')}"
                    )
            if fk_strs:
                lines.append(f"  Foreign Keys: {', '.join(fk_strs)}")
        
        lines.append("")
    
    return "\n".join(lines)


def format_plan_for_prompt(plan: Dict) -> str:
    """Formats the query plan into a readable string."""
    
    lines = []
    
    lines.append(f"Intent: {plan.get('intent', 'select').upper()}")
    
    tables = plan.get("tables_considered", [])
    if tables:
        lines.append(f"Tables: {', '.join(tables)}")
    
    if plan.get("needs_join"):
        lines.append("Join Required: Yes")
    
    if plan.get("aggregation"):
        lines.append(f"Aggregation: {plan['aggregation']}")
    
    if plan.get("grouping"):
        lines.append(f"Group By: {plan['grouping']}")
    
    if plan.get("sorting"):
        lines.append(f"Sorting: {plan['sorting']}")
    
    if plan.get("limit"):
        lines.append(f"Limit: {plan['limit']}")
    
    if plan.get("distinct"):
        lines.append("Distinct: Yes")
    
    if plan.get("filters_detected"):
        hints = plan.get("filter_hints", [])
        if hints:
            lines.append(f"Filters: {', '.join(hints[:3])}")
    
    reasoning = plan.get("reasoning_summary", [])
    if reasoning:
        lines.append("")
        lines.append("Reasoning:")
        for i, step in enumerate(reasoning[:5], 1):
            lines.append(f"  {i}. {step}")
    
    return "\n".join(lines)


def parse_llm_response(response: str) -> Dict:
    """
    Parses the LLM response to extract REASONING and SQL.
    
    Args:
        response: Raw LLM response
    
    Returns:
        dict with 'sql' and 'reasoning'
    
    Raises:
        SQLGenerationError: If required sections are missing
    """
    
    response = response.strip()
    
    # Multi-pattern matching
    patterns = [
        # Standard format
        (r"(?i)REASONING:?\s*(.*?)(?=SQL:|```sql|```)", r"(?i)SQL:?\s*(.*)$"),
        # With code block
        (r"(?i)REASONING:?\s*(.*?)(?=```)", r"```sql?\s*(.*?)\s*```"),
        # Just SQL block
        (None, r"```sql?\s*(.*?)\s*```"),
    ]
    
    reasoning = ""
    sql = ""
    
    for reasoning_pattern, sql_pattern in patterns:
        if reasoning_pattern:
            reasoning_match = re.search(reasoning_pattern, response, re.DOTALL)
            if reasoning_match:
                reasoning = reasoning_match.group(1).strip()
        
        sql_match = re.search(sql_pattern, response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1).strip()
            break
    
    # Final fallback: look for SELECT/WITH
    if not sql:
        # Try to find SQL starting with SELECT or WITH
        sql_match = re.search(
            r'(?i)((?:WITH|SELECT)\s+.+?)(?:$|\n\n)',
            response,
            re.DOTALL
        )
        if sql_match:
            sql = sql_match.group(1).strip()
            
            # Extract reasoning as everything before SQL
            sql_start = response.lower().find(sql.lower()[:20])
            if sql_start > 0:
                reasoning = response[:sql_start].strip()
                # Clean up reasoning
                reasoning = re.sub(r'^(?:REASONING:?|SQL:?)\s*', '', reasoning, flags=re.IGNORECASE)
    
    # Clean the SQL
    sql = clean_sql(sql)
    
    if not sql:
        raise SQLGenerationError(
            "Failed to extract SQL from LLM response. "
            "The model did not return a valid SQL query."
        )
    
    if not reasoning:
        reasoning = "Query generated based on the provided schema and user question."
    
    return {
        "sql": sql,
        "reasoning": reasoning
    }


def clean_sql(sql: str) -> str:
    """Cleans SQL by removing markdown, code fences, comments, and extra whitespace/prose."""
    
    if not sql:
        return ""
    
    # Remove code fences
    sql = re.sub(r"```sql?\s*", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```\s*$", "", sql)
    sql = re.sub(r"```", "", sql)
    
    # Remove inline comments
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    
    # Remove block comments
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    
    # Find start
    match = re.search(r'(?i)\b((?:WITH|SELECT)\s+.+)', sql, re.DOTALL)
    if match:
        sql = match.group(1)
    
    # 1. Truncate at first semicolon
    if ";" in sql:
        sql = sql.split(";")[0]
        
    # 2. Truncate at common prose indicators (if no semicolon was found or prose followed)
    # Detects: "Given...", "Note:...", "The query...", "Explanation..."
    prose_indicators = [
        r'\n\s*Given\b',
        r'\n\s*Note\b',
        r'\n\s*Explanation\b',
        r'\n\s*The query\b',
        r'\n\s*This query\b',
        r'\n\s*Here\b'
    ]
    for indicator in prose_indicators:
        parts = re.split(indicator, sql, flags=re.IGNORECASE)
        if len(parts) > 1:
            sql = parts[0]
    
    # Clean up whitespace
    sql = " ".join(sql.split())
    
    return sql.strip()


# Backward compatibility
def generate_sql(llm_client, plan, schema, question):
    """Legacy function - returns only SQL string."""
    result = generate_sql_with_reasoning(llm_client, plan, schema, question)
    return result["sql"]
