"""
Enhanced Ambiguity Detector

Detects vague or ambiguous terms in user queries and generates
clarification questions to improve query accuracy.
"""

import re
from typing import Tuple, Optional, Dict, List


# Comprehensive ambiguity patterns with categorized interpretations
AMBIGUOUS_PATTERNS: Dict[str, Dict] = {
    # Ranking ambiguity
    "top": {
        "options": ["highest value", "most frequent", "most recent", "highest rated"],
        "clarification": "When you say 'top', do you mean by {options}?",
        "category": "ranking"
    },
    "best": {
        "options": ["highest rating", "highest revenue", "most popular", "highest quantity"],
        "clarification": "What defines 'best' in this context? ({options})",
        "category": "ranking"
    },
    "highest": {
        "options": ["maximum value", "maximum count", "highest total"],
        "clarification": "When you say 'highest', do you mean {options}?",
        "category": "ranking"
    },
    "lowest": {
        "options": ["minimum value", "minimum count", "lowest total"],
        "clarification": "When you say 'lowest', do you mean {options}?",
        "category": "ranking"
    },
    "most": {
        "options": ["highest count", "highest value", "most frequent"],
        "clarification": "'Most' could mean different things. Do you mean {options}?",
        "category": "ranking"
    },
    "least": {
        "options": ["lowest count", "lowest value", "least frequent"],
        "clarification": "When you say 'least', what measure are you referring to? ({options})",
        "category": "ranking"
    },
    
    # Time ambiguity
    "latest": {
        "options": ["most recent date", "last inserted record", "newest entry"],
        "clarification": "When you say 'latest', do you mean {options}?",
        "category": "time"
    },
    "recent": {
        "options": ["last 7 days", "last 30 days", "last quarter", "last year"],
        "clarification": "How recent? ({options})",
        "category": "time"
    },
    "old": {
        "options": ["oldest by date", "created longest ago", "first entries"],
        "clarification": "When you say 'old', do you mean {options}?",
        "category": "time"
    },
    
    # Quantity ambiguity
    "few": {
        "options": ["less than 5", "less than 10", "bottom 10%"],
        "clarification": "How many would you consider 'few'? ({options})",
        "category": "quantity"
    },
    "many": {
        "options": ["more than 10", "more than 50", "top 10%"],
        "clarification": "How many would you consider 'many'? ({options})",
        "category": "quantity"
    },
    "some": {
        "options": ["approximately 5", "approximately 10", "a sample"],
        "clarification": "Could you specify a rough number for 'some'? ({options})",
        "category": "quantity"
    },
    
    # Comparison ambiguity
    "better": {
        "options": ["higher rating", "higher sales", "better performance"],
        "clarification": "Better in what way? ({options})",
        "category": "comparison"
    },
    "worse": {
        "options": ["lower rating", "lower sales", "worse performance"],
        "clarification": "Worse in what way? ({options})",
        "category": "comparison"
    },
    "similar": {
        "options": ["same category", "similar value range", "related items"],
        "clarification": "Similar based on what criteria? ({options})",
        "category": "comparison"
    },
    
    # Aggregation ambiguity
    "average": {
        "options": ["mean", "median", "mode"],
        "clarification": "Which type of average? ({options})",
        "category": "aggregation",
        "skip_common": True  # 'average' is usually clear, skip unless ambiguous context
    },
    "total": {
        "options": ["sum of values", "count of records", "running total"],
        "clarification": "When you say 'total', do you mean {options}?",
        "category": "aggregation",
        "skip_common": True
    },
    
    # Size/scope ambiguity
    "large": {
        "options": ["above average size", "top 25%", "larger than threshold"],
        "clarification": "How would you define 'large'? ({options})",
        "category": "size"
    },
    "small": {
        "options": ["below average size", "bottom 25%", "smaller than threshold"],
        "clarification": "How would you define 'small'? ({options})",
        "category": "size"
    },
    "significant": {
        "options": ["statistically significant", "above average", "notable difference"],
        "clarification": "What would be considered 'significant'? ({options})",
        "category": "size"
    },
    
    # Status ambiguity
    "active": {
        "options": ["currently active status", "has recent activity", "not archived"],
        "clarification": "What defines 'active' in this context? ({options})",
        "category": "status"
    },
    "popular": {
        "options": ["most viewed", "most purchased", "highest rated", "trending"],
        "clarification": "Popular by what measure? ({options})",
        "category": "status"
    }
}


# Patterns that often indicate clear intent (reduce false positives)
CLEAR_CONTEXT_PATTERNS = [
    r"top \d+",           # "top 5" is clear
    r"first \d+",         # "first 10" is clear
    r"last \d+",          # "last 3" is clear
    r"highest \w+ by",    # "highest sales by" is clear
    r"most \w+ per",      # "most orders per" is clear
    r"average of \w+",    # "average of prices" is clear
]


def detect_ambiguity(query: str) -> Tuple[bool, Optional[Dict]]:
    """
    Detects ambiguity in a user query.
    
    Args:
        query: The user's natural language query
    
    Returns:
        Tuple of:
        - bool: True if ambiguity detected
        - dict or None: Clarification data if ambiguous, containing:
            - term: The ambiguous word
            - options: List of possible interpretations
            - question: Clarification question to ask
            - category: Type of ambiguity
    """
    
    if not query:
        return False, None
    
    query_lower = query.lower()
    
    # Check if context makes the query clear
    for pattern in CLEAR_CONTEXT_PATTERNS:
        if re.search(pattern, query_lower):
            # Extract what follows to see if it's actually clear
            # For now, we'll consider these patterns as clear
            return False, None
    
    # Check for ambiguous terms
    for term, config in AMBIGUOUS_PATTERNS.items():
        # Word boundary check to avoid partial matches
        pattern = rf'\b{term}\b'
        if re.search(pattern, query_lower):
            
            # Skip terms marked as commonly clear
            if config.get("skip_common"):
                # Check if additional context exists that makes it clear
                has_context = any([
                    f"{term} of" in query_lower,
                    f"{term} by" in query_lower,
                    f"{term} for" in query_lower,
                ])
                if has_context:
                    continue
            
            options = config["options"]
            options_str = ", ".join(options)
            
            # Format clarification question
            question = config["clarification"].format(options=options_str)
            
            return True, {
                "term": term,
                "options": options,
                "question": question,
                "category": config.get("category", "general")
            }
    
    return False, None


def should_clarify(query: str, schema: Optional[Dict] = None) -> Tuple[bool, Optional[Dict]]:
    """
    Enhanced ambiguity detection that considers schema context.
    
    If schema is provided, checks if ambiguous terms might refer to
    actual column names, reducing false positives.
    
    Args:
        query: User query
        schema: Optional database schema
    
    Returns:
        Same as detect_ambiguity
    """
    
    is_ambiguous, data = detect_ambiguity(query)
    
    if not is_ambiguous or not schema:
        return is_ambiguous, data
    
    # Check if the ambiguous term is actually a column name
    term = data["term"]
    all_columns = []
    for table_info in schema.values():
        all_columns.extend([col.lower() for col in table_info.get("columns", [])])
    
    if term in all_columns:
        # The term is a column name, not ambiguous in this context
        return False, None
    
    return is_ambiguous, data


def get_clarification_examples() -> List[Dict]:
    """
    Returns example clarifications for UI hints or testing.
    """
    return [
        {
            "query": "Show me the top customers",
            "clarification": "When you say 'top', do you mean by highest value, most frequent, most recent, or highest rated?",
            "responses": ["highest value", "most orders", "most revenue"]
        },
        {
            "query": "Find recent orders",
            "clarification": "How recent? (last 7 days, last 30 days, last quarter, last year)",
            "responses": ["last week", "this month", "past 30 days"]
        },
        {
            "query": "Which products are popular?",
            "clarification": "Popular by what measure? (most viewed, most purchased, highest rated, trending)",
            "responses": ["most sold", "highest rated", "most viewed"]
        }
    ]
