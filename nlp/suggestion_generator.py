"""
Suggestion Generator

Uses LLM to analyze database schema and user context to generate:
1. Initial "Starter" questions when a DB is uploaded.
2. "Related" or "Refined" follow-up questions after a query.
"""

from typing import List, Dict

def generate_initial_questions(llm_client, schema: Dict) -> List[str]:
    """
    Analyzes the schema to generate 4 diverse starting questions.
    """
    
    # Create a compact schema summary
    tables = list(schema.keys())
    schema_summary = f"Tables: {', '.join(tables)}\n"
    
    for t in tables[:4]:  # Focus on key tables
        cols = schema[t].get("columns", [])
        schema_summary += f"- {t}: {', '.join(cols[:5])}...\n"

    prompt = f"""You are a SQL expert. Analyze this database schema and generate 4 diverse, interesting questions a user might want to ask.
    
SCHEMA:
{schema_summary}

RULES:
1. Generate natural language questions (no SQL).
2. Covering different complexity levels:
   - 1 Simple (Count/List)
   - 1 Moderate (Group By/Top N)
   - 1 Complex (Join/Filter)
   - 1 Business Insight (Trends/Performance)
3. Keep them concise (under 15 words).
4. Return ONLY the 4 questions, one per line.

QUESTIONS:
"""

    try:
        response = llm_client.generate(prompt, temperature=0.7)
        questions = [q.strip("- ").strip() for q in response.strip().split("\n") if q.strip()]
        return questions[:4]
    except:
        # Fallback if LLM fails
        return [
            f"Show me the first 10 {tables[0]}",
            f"How many {tables[0]} are there?",
            f"List all {tables[1] if len(tables) > 1 else tables[0]}",
            "What tables are in this database?"
        ]


def generate_related_questions(
    llm_client, 
    original_question: str, 
    schema: Dict
) -> List[str]:
    """
    Generates 3 relevant follow-up or refined questions based on the previous interaction.
    """
    
    prompt = f"""Based on the user's last question about a database, suggest 3 relevant follow-up questions.

LAST QUESTION: "{original_question}"

RULES:
1. Suggest questions that dig deeper (e.g., if asked for "total sales", suggest "sales by year").
2. Suggest questions that filter or slice the data differently.
3. Suggest one "Insight" question.
4. Keep them concise.
5. Return ONLY 3 questions, one per line.

SUGGESTIONS:
"""

    try:
        response = llm_client.generate(prompt, temperature=0.6)
        questions = [q.strip("- ").strip() for q in response.strip().split("\n") if q.strip()]
        return questions[:3]
    except:
        return []
