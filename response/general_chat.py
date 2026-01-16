"""
General Chat Handler

Handles non-SQL questions like greetings, summaries, and general help.
Uses database schema context to provide relevant answers without querying.
"""

from typing import Dict, List

def handle_general_chat(llm_client, question: str, schema: Dict) -> Dict:
    """
    Generates a response for general chat questions using schema context.
    """
    
    # Create a lightweight schema summary
    tables = list(schema.keys())
    schema_summary = f"Database contains {len(tables)} tables: {', '.join(tables)}"
    
    table_details = []
    for t in tables[:5]:  # Summarize top 5 tables for context
        cols = schema[t].get("columns", [])
        table_details.append(f"- {t}: {', '.join(cols[:5])}...")
    
    context = "\n".join(table_details)
    
    prompt = f"""You are a helpful SQL Assistant powered by a database.
The user asked a general question (not a specific SQL query).
Answer them helpfully using the database context if relevant.

DATABASE CONTEXT:
{schema_summary}
{context}

USER QUESTION:
{question}

INSTRUCTIONS:
1. If asked about the dataset, summarize what kind of data is in the tables (e.g., "This appears to be a music store database...").
2. If it's a greeting, welcome them and mention what you can query.
3. If asking for help, suggest 3 sample queries relevant to this specific schema.
4. Keep it conversational and helpful.
5. Do NOT generate SQL code blocks.

YOUR ANSWER:
"""

    answer = llm_client.generate(prompt, temperature=0.7)
    
    return {
        "answer": answer.strip(),
        "reasoning": "Processed as General Chat (no SQL executed)",
        "sql": "-- No SQL generated for general chat",
        "columns": [],
        "rows": [],
        "row_count": 0
    }
