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
    
    # Infer semantic flag values from schema
    value_inference_guide = infer_semantic_flag_values(schema, question)
    
    prompt = _build_prompt(
        schema_text=schema_text,
        plan_text=plan_text,
        question=question,
        complexity=complexity,
        retry_context=retry_context,
        value_inference_guide=value_inference_guide
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
    retry_context: str = "",
    value_inference_guide: str = ""
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

    return f"""You are a reasoning-first Natural Language to SQL expert.

Your primary goal is NOT to generate SQL immediately.
Your goal is to FIRST understand the user's intent and constraints,
then generate a safe, correct, OPTIMIZED, read-only SQL query.

═══════════════════════════════════════════════════════════════════
                        MANDATORY 5-STEP PIPELINE
═══════════════════════════════════════════════════════════════════

STEP 1: INTENT CLASSIFICATION (Already done - see QUERY PLAN below)
Intent Type: {plan_text}

STEP 2: REASONING PLAN (YOU MUST DO THIS FIRST - VISIBLE TO USER)
Before writing SQL, produce a short reasoning plan that explains:
- What entity is being queried
- What constraints must be enforced
- Whether the condition is existential, universal, or absence-based
- Which SQL pattern is required
- Your optimization strategy

STEP 3: SQL GENERATION (OPTIMIZED - BEST VERSION)
Generate the BEST POSSIBLE query following these rules:

═══════════════════════════════════════════════════════════════════
                         OPTIMIZATION RULES
═══════════════════════════════════════════════════════════════════

INTENT-BASED PATTERN SELECTION:
✅ EXISTENTIAL ("has", "with", "containing"):
   - Use EXISTS instead of JOIN when only checking existence
   - EXISTS stops at first match (faster than JOIN)
   - Example: SELECT c.* FROM Customer c WHERE EXISTS (SELECT 1 FROM Invoice i WHERE i.CustomerId = c.CustomerId)

✅ UNIVERSAL ("only", "every", "all"):
   - Use NOT EXISTS for anti-joins (most efficient)
   - Example: Customers who only bought Rock → use NOT EXISTS to exclude other genres

✅ SET_INTERSECTION ("both X and Y"):
   - Use GROUP BY + HAVING COUNT(DISTINCT ...) = N (single pass)
   - Avoid multiple subqueries
   - Example: GROUP BY customer HAVING COUNT(DISTINCT genre) = 2

✅ ABSENCE ("never", "without", "no"):
   - Use NOT EXISTS or LEFT JOIN + IS NULL  
   - NOT EXISTS is usually faster
   - Example: SELECT c.* FROM Customer c WHERE NOT EXISTS (SELECT 1 FROM Invoice i WHERE i.CustomerId = c.CustomerId)

✅ AGGREGATION/RANKING ("top", "most", "average"):
   - Use ORDER BY + LIMIT (no DISTINCT RANK needed)
   - Apply LIMIT to cap results
   - Example: ORDER BY total DESC LIMIT 5

PERFORMANCE OPTIMIZATIONS:
1. ❌ NEVER use SELECT *
2. ✅ Select only needed columns by name
3. ✅ Use EXISTS over IN for subqueries
4. ✅ Avoid DISTINCT when GROUP BY achieves same result
5. ✅ Filter on indexed columns (primary keys, foreign keys) in WHERE
6. ✅ Apply WHERE filters before JOINs when possible
7. ✅ Use LIMIT for ranking queries
8. ✅ Use CTEs (WITH clause) for complex multi-step queries (readability)

═══════════════════════════════════════════════════════════════════
                   SCHEMA-AWARE VALUE INFERENCE
═══════════════════════════════════════════════════════════════════

When using semantic flags (discontinued, active, status, shipped, etc.):

❌ NEVER hardcode values without schema inspection:
   - Don't assume: discontinued = '0' or '1'
   - Don't assume: active = 'Y' or 'N'
   - Don't assume: status = 'ACTIVE' or 'INACTIVE'

✅ ALWAYS infer from schema inspection:
   1. Check the column's data type (INTEGER, BOOLEAN, TEXT)
   2. Infer the representation:
      - INTEGER → 0 = false/off, 1 = true/on
      - BOOLEAN → TRUE/FALSE (or 1/0 in SQLite)
      - TEXT → Status values (inspect schema/context)
   3. Explain your inference in REASONING

{value_inference_guide}

═══════════════════════════════════════════════════════════════════
                         CRITICAL SQL RULES
═══════════════════════════════════════════════════════════════════

1. OUTPUT FORMAT (MANDATORY):
   You MUST provide your response in EXACTLY this format:
   
   REASONING:
   - Entity: What table/entity is being queried
   - Constraints: What conditions must be satisfied
   - Value Inference: How semantic flags are represented (if applicable)
   - Intent Type: EXISTENTIAL | UNIVERSAL | SET_INTERSECTION | ABSENCE | AGGREGATION
   - SQL Pattern: EXISTS | NOT EXISTS | GROUP BY + HAVING | JOIN | LEFT JOIN + NULL
   - Optimization: Why this pattern is most efficient
   
   SQL:
   <Your optimized SQLite query - NO markdown, NO comments>
   
   ⚠️ BOTH SECTIONS ARE REQUIRED

2. SAFETY RULES:
   - Generate ONLY valid SQLite SQL
   - Use SELECT or WITH...SELECT only
   - NEVER use INSERT, UPDATE, DELETE, DROP, ALTER
   - NO SQL comments (--) or markdown code fences (```)
   - Handle NULL correctly (IS NULL / IS NOT NULL)

3. READABILITY RULES:
   - Use meaningful table aliases (c for Customer, i for Invoice)
   - Qualify all column names in JOINs (c.CustomerId, not CustomerId)
   - For complex queries, use CTEs (WITH clause) for clarity

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


def infer_semantic_flag_values(schema: Dict, question: str) -> str:
    """
    Analyzes schema to infer how semantic flags are represented.
    Returns guidance text for the LLM on value inference.
    """
    
    # Common semantic flag patterns to look for
    flag_keywords = {
        'discontinued': ['discontinued', 'discontinue', 'disc'],
        'active': ['active', 'is_active', 'isactive'],
        'status': ['status', 'state'],
        'shipped': ['shipped', 'is_shipped'],
        'completed': ['completed', 'complete', 'is_complete'],
        'enabled': ['enabled', 'is_enabled'],
        'verified': ['verified', 'is_verified'],
        'deleted': ['deleted', 'is_deleted'],
        'archived': ['archived', 'is_archived'],
        'published': ['published', 'is_published']
    }
    
    # Find relevant flags in schema
    found_flags = []
    
    for table, info in schema.items():
        columns = info.get("columns", [])
        column_types = info.get("column_types", {})
        
        for col in columns:
            col_lower = col.lower()
            col_type = column_types.get(col, "").upper()
            
            # Check if this column matches a semantic flag pattern
            for concept, patterns in flag_keywords.items():
                if any(pattern in col_lower for pattern in patterns):
                    # Determine likely representation based on data type
                    if 'BOOLEAN' in col_type or 'BOOL' in col_type:
                        inference = f"{col}: BOOLEAN type → Use TRUE/FALSE or 1/0"
                    elif 'INT' in col_type or 'TINYINT' in col_type or 'SMALLINT' in col_type:
                        inference = f"{col}: INTEGER type → Likely 0 = false/{concept} off, 1 = true/{concept} on"
                    elif 'TEXT' in col_type or 'VARCHAR' in col_type or 'CHAR' in col_type:
                        inference = f"{col}: TEXT type → Check for status values like 'active'/'inactive', 'Y'/'N', etc."
                    else:
                        inference = f"{col}: {col_type} → Inspect schema for representation"
                    
                    found_flags.append({
                        'table': table,
                        'column': col,
                        'type': col_type,
                        'concept': concept,
                        'inference': inference
                    })
    
    if not found_flags:
        return ""
    
    # Build guidance text
    lines = []
    lines.append("SCHEMA-AWARE VALUE INFERENCE GUIDANCE:")
    lines.append("The following semantic flags were detected in the schema:")
    lines.append("")
    
    for flag in found_flags:
        lines.append(f"  • {flag['table']}.{flag['column']} ({flag['type']}):")
        if 'INT' in flag['type']:
            lines.append(f"    → INTEGER flag: Use 0 = not {flag['concept']}, 1 = {flag['concept']}")
        elif 'BOOL' in flag['type']:
            lines.append(f"    → BOOLEAN flag: Use TRUE = {flag['concept']}, FALSE = not {flag['concept']}")
        elif 'TEXT' in flag['type'] or 'VARCHAR' in flag['type'] or 'CHAR' in flag['type']:
            lines.append(f"    → TEXT flag: Infer status values from context (e.g., 'active'/'inactive')")
        lines.append("")
    
    lines.append("IMPORTANT:")
    lines.append("  - Do NOT hardcode arbitrary values like '0', '1', 'Y', 'N' without inference")
    lines.append("  - Explain your value inference in the REASONING section")
    lines.append("  - Example: \"Since 'discontinued' is INTEGER, I infer: discontinued = 1 means discontinued\"")
    
    return "\n".join(lines)


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
    
    # NEW: Intent Type (5-type classification)
    intent_type = plan.get("intent_type")
    if intent_type:
        lines.append(f"Intent Type: {intent_type}")
    
    # NEW: Optimization Strategy
    optimization = plan.get("optimization_strategy")
    if optimization:
        lines.append(f"Optimization Strategy: {optimization}")
    
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
        
        sql_match = re.search(sql_pattern, response, re.DOTALL | re.MULTILINE)
        if sql_match:
            sql = sql_match.group(1).strip()
            # If we matched a block, check if it's actually SQL (contains SELECT/WITH at start)
            keywords = ['SELECT', 'WITH', 'PRAGMA', 'EXPLAIN']
            if any(k in sql.upper() for k in keywords):
                break
            else:
                # Reset if it looks like prose
                sql = ""

    
    # Final fallback: look for SELECT/WITH
    if not sql:
        # Try to find SQL starting with SELECT or WITH at the BEGINNING of a line
        # This prevents matching "with" inside sentences
        sql_match = re.search(
            r'(?im)^\s*((?:WITH|SELECT)\s+.+?)(?:$|(?:\n\s*\n))',
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
    
    # Check for placeholder messages that aren't real SQL
    if len(sql.split()) < 5 and not any(k in sql.upper() for k in ["SELECT", "WITH", "PRAGMA"]):
        sql = ""

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
    
    # Find start - anchor to start of string or start of line
    # Must be followed by a space and then some typical SQL-starting characters
    # If it starts with "SELECT that ..." or "WITH the ...", it's likely prose
    prose_starts = [
        r"(?i)\bSELECT\s+(?:that|returns|is|for|to|specifically|only|just)\b",
        r"(?i)\bWITH\s+(?:the|this|all|these|regard|respect)\b",
    ]
    
    # Check if the FIRST match is actually prose
    first_word_match = re.search(r'(?i)^\s*(\w+)\b', sql)
    if first_word_match:
        first_word = first_word_match.group(1).upper()
        if first_word in ["SELECT", "WITH", "PRAGMA", "EXPLAIN"]:
            is_prose = False
            for p_pattern in prose_starts:
                if re.search(p_pattern, sql[:100]):
                    is_prose = True
                    break
            
            if is_prose:
                # It's likely a sentence starting with "Select..."
                # Find a LATER occurrence of "SQL:" or a backtick block
                sql_marker_match = re.search(r'(?i)SQL:\s*(.+)', sql, re.DOTALL)
                if sql_marker_match:
                    sql = sql_marker_match.group(1)
                else:
                    # Or find a line that is CLEARLY SQL (WITH name AS or SELECT col)
                    lines = sql.split('\n')
                    for i, line in enumerate(lines):
                        if i > 0 and (re.search(r'^\s*SELECT\s+', line, re.IGNORECASE) or 
                                      re.search(r'^\s*WITH\s+\w+\s+AS\s*\(', line, re.IGNORECASE)):
                            sql = "\n".join(lines[i:])
                            break

    # Anchor to start of line for keywords
    # WITH must be followed by name AS (
    match = re.search(r'(?im)^\s*(SELECT\s+.+|WITH\s+\w+\s+AS\s*\(.+|PRAGMA\s+.+|EXPLAIN\s+.+)', sql, re.DOTALL)
    if match:
        sql = match.group(1)
    else:
        # Fallback for mid-string start
        # SELECT is safer than WITH for mid-string
        match = re.search(r'(?i)\b(SELECT\s+[a-zA-Z0-9_"`\'\[(*].+)', sql, re.DOTALL)
        if match:
             candidate = match.group(1)
             common_prose_words = {"that", "returns", "the", "a", "is", "for", "to", "this", "it", "was", "will", "would"}
             words_in_start = set(candidate.lower().split()[:10])
             if not (words_in_start & common_prose_words):
                 sql = candidate
        else:
             # Last ditch for WITH
             match = re.search(r'(?i)\b(WITH\s+\w+\s+AS\s*\(.+)', sql, re.DOTALL)
             if match:
                 sql = match.group(1)



    
    # 1. Handle semicolons: only truncate if followed by prose
    # If a semicolon is followed by a SELECT, it's likely a malformed single statement
    if ";" in sql:
        parts = sql.split(";")
        if len(parts) > 1:
            # If the next part starts with SELECT/WITH, it's likely a malformed single statement
            # We'll just remove the semicolon and keep going
            next_part = parts[1].strip().lower()
            if next_part.startswith(("select", "with")):
                sql = " ".join(parts)
            else:
                # Otherwise truncate
                sql = parts[0]

        
    # 2. Truncate at common prose indicators (only if they appear after the possible SQL start)
    prose_indicators = [
        r'\n\s*Given\b',
        r'\n\s*Note\b',
        r'\n\s*Explanation\b',
        r'\n\s*The query\b',
        r'\n\s*This query\b',
        r'\n\s*Here\b',
        r'\n\s*In this\b',
        r'\n\s*I have\b',
        r'\n\s*Please\b'
    ]
    for indicator in prose_indicators:
        parts = re.split(indicator, sql, flags=re.IGNORECASE)
        if len(parts) > 1:
            sql = parts[0]
    
    # Final check: if it contains "SQL:" mid-string, it might be the separator we missed
    if "SQL:" in sql:
        parts = sql.split("SQL:")
        if len(parts) > 1 and ("SELECT" in parts[1].upper() or "WITH" in parts[1].upper()):
            sql = parts[1]

    # Heuristic: if it's very long and contains " because " or " is " or other common prose, 
    # and doesn't have enough SQL keywords, it's probably still prose.
    if len(sql.split()) > 30:
        sql_keywords = {"SELECT", "FROM", "WHERE", "JOIN", "GROUP", "ORDER", "LIMIT", "WITH", "AS"}
        words_upper = set(sql.upper().split())
        if len(words_upper & sql_keywords) < 3:
             # Too many words, too few keywords -> likely prose
             return ""

    # Clean up whitespace
    sql = " ".join(sql.split())
    
    return sql.strip()




# Backward compatibility
def generate_sql(llm_client, plan, schema, question):
    """Legacy function - returns only SQL string."""
    result = generate_sql_with_reasoning(llm_client, plan, schema, question)
    return result["sql"]
