"""
Intent Classifier

Uses LLM to classify user questions into:
1. SQL_QUERY: Requires database access
2. GENERAL_CHAT: General conversation, greetings, or high-level summaries
"""

from typing import Dict, Tuple

def classify_intent(llm_client, question: str) -> Tuple[str, str]:
    """
    Classifies the user's question intent.
    
    Returns:
        Tuple of (intent_type, reasoning)
        intent_type: 'SQL_QUERY' or 'GENERAL_CHAT'
    """
    
    # Fast regex checks for obvious non-SQL
    q = question.lower().strip()
    
    # Greetings
    if q in ["hi", "hello", "hey", "greetings", "good morning", "good evening"]:
        return "GENERAL_CHAT", "Detected greeting"
    
    # Help/Capabilities
    if any(x in q for x in ["what can you do", "help me", "how to use", "capabilities"]):
        return "GENERAL_CHAT", "Detected help request"
    
    # Summarization requests
    if any(x in q for x in ["what is this dataset", "explain this database", "summary of data", "tell me about the data"]):
        return "GENERAL_CHAT", "Detected dataset summary request"

    # LLM Classification for nuanced cases
    prompt = f"""You are an intent classifier for a SQL Assistant.
Determine if the user's input requires executing a SQL query on the database or if it is a general chat/greeting/summary request.

USER INPUT: "{question}"

RULES:
- "Show me users", "How many...", "List..." -> SQL_QUERY
- "What is this dataset?", "Hi", "Help", "Explain the schema" -> GENERAL_CHAT
- "Who are the customers?" -> SQL_QUERY
- "Analyze the sales" -> SQL_QUERY

RESPONSE FORMAT:
One word: SQL_QUERY or GENERAL_CHAT
"""

    try:
        response = llm_client.generate(prompt, temperature=0.1, max_tokens=10)
        intent = response.strip().upper()
        
        if "SQL" in intent:
            return "SQL_QUERY", "LLM classified as requiring database access"
        else:
            return "GENERAL_CHAT", "LLM classified as general conversation"
            
    except Exception as e:
        # Default to SQL if classification fails, as that's the core function
        return "SQL_QUERY", "Classification failed, defaulting to SQL"
