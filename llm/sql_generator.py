from llm.prompt_templates import sql_generation_prompt

def generate_sql(llm_client, plan, schema, question):
    prompt = f"""
You are a professional SQL expert.

CRITICAL RULES:
- Generate ONLY valid SQLite SQL
- Use ONLY SELECT statements (or WITH + SELECT)
- NEVER use READ, WRITE, PRAGMA, INSERT, UPDATE, DELETE
- Do NOT invent SQL keywords
- Do NOT include comments or explanations
- Output SQL ONLY

Schema:
{schema}

Plan:
{plan}

User Question:
{question}

SQL:
"""
    return llm_client.generate(prompt)
