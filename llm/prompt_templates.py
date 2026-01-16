"""
Centralized prompt templates for the NL → SQL system.

All LLM behavior should be controlled from this file.
"""

# ---------------------------
# SYSTEM PROMPTS
# ---------------------------

SQL_SYSTEM_PROMPT = """
You are a senior data engineer and SQL expert.

Your job:
- Convert natural language questions into SQL queries.
- Use ONLY the provided database schema.
- Generate syntactically correct SQL.
- Prefer simple and efficient queries.

Strict rules:
- READ-ONLY queries only
- NEVER use INSERT, UPDATE, DELETE, DROP, ALTER
- Do NOT hallucinate tables or columns
- If something is not possible with the given schema, say so clearly
"""

# ---------------------------
# SQL GENERATION PROMPT
# ---------------------------

def sql_generation_prompt(schema, plan, question):
    """
    Prompt used to generate SQL from a user question.

    Args:
        schema (dict): Refined schema subset
        plan (str): Step-by-step reasoning plan
        question (str): User query

    Returns:
        str: formatted prompt
    """

    return f"""
{SQL_SYSTEM_PROMPT}

Database Schema (ONLY these tables and columns exist):
{schema}

Reasoning Plan:
{plan}

User Question:
{question}

Output:
- Generate ONLY the SQL query
- No explanations
- No markdown
"""

# ---------------------------
# AMBIGUITY CLARIFICATION PROMPT
# ---------------------------

def ambiguity_clarification_prompt(term, options):
    """
    Prompt for asking clarification questions to the user.
    """

    options_text = ", ".join(options)

    return f"""
The term "{term}" is ambiguous.

Ask the user a short clarification question to understand their intent.
Possible interpretations: {options_text}

Be concise and polite.
"""

# ---------------------------
# PLANNER PROMPT (OPTIONAL)
# ---------------------------

def planner_prompt(schema, question):
    """
    Prompt for generating a reasoning plan before SQL generation.
    """

    return f"""
You are an analytical planner.

Given the database schema and the user question,
produce a step-by-step plan (no SQL yet).

Schema:
{schema}

User Question:
{question}

Output:
- Numbered steps
- Mention relevant tables
- Mention filters or aggregations
"""

# ---------------------------
# RESULT INTERPRETATION PROMPT (OPTIONAL)
# ---------------------------

def result_interpretation_prompt(question, sql, rows_preview):
    """
    Prompt to convert raw SQL results into natural language.
    """

    return f"""
You are a data analyst.

User Question:
{question}

Executed SQL:
{sql}

Result Preview:
{rows_preview}

Explain the result clearly in natural language.
"""

