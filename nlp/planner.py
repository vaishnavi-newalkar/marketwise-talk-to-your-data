"""
Enhanced Query Planner

Creates structured reasoning plans for SQL generation.
Handles all complexity levels:
- Simple: Single table queries
- Moderate: JOINs and aggregations
- Complex: Subqueries, negation, exclusion
- Multi-step: "Both X and Y" type queries
"""

import re
from typing import Dict, List, Optional


def create_plan(question: str, schema: dict) -> dict:
    """
    Creates a comprehensive structured reasoning plan for SQL generation.
    
    Args:
        question: User's natural language question
        schema: Refined database schema
    
    Returns:
        dict: Detailed query plan
    """
    
    q = question.lower()
    tables = list(schema.keys())
    
    plan = {
        "intent": "select",
        "complexity": "simple",
        "tables_considered": tables,
        "needs_join": len(tables) > 1,
        "filters_detected": False,
        "filter_hints": [],
        "aggregation": None,
        "grouping": None,
        "sorting": None,
        "limit": None,
        "distinct": False,
        "negation": False,
        "intersection": False,
        "subquery_needed": False,
        "reasoning_summary": []
    }
    
    # Analyze query components
    plan = _detect_intent(q, plan)
    plan = _detect_complexity_patterns(q, plan)
    plan = _detect_filters(q, plan, schema)
    plan = _detect_aggregation(q, plan)
    plan = _detect_grouping(q, plan, schema)
    plan = _detect_sorting_and_limits(q, plan)
    plan = _detect_distinct(q, plan)
    plan = _detect_negation(q, plan)
    plan = _detect_intersection(q, plan)
    
    # Determine overall complexity
    plan["complexity"] = _calculate_complexity(plan)
    
    # Add base reasoning
    plan["reasoning_summary"].insert(
        0,
        f"Identified {len(tables)} relevant table(s): {', '.join(tables)}"
    )
    
    if plan["needs_join"]:
        plan["reasoning_summary"].append(
            "Multiple tables detected - JOIN operations will be required."
        )
    
    if plan["complexity"] in ["complex", "multi_step"]:
        plan["reasoning_summary"].append(
            f"Query complexity: {plan['complexity'].upper()} - may require subqueries or CTEs."
        )
    
    return plan


def _detect_intent(question: str, plan: dict) -> dict:
    """Detect the primary intent of the query."""
    
    # Count intent
    count_patterns = [
        r"\bhow many\b", r"\bcount\b", r"\bnumber of\b", 
        r"\btotal number\b", r"\bhow much\b"
    ]
    for pattern in count_patterns:
        if re.search(pattern, question):
            plan["intent"] = "count"
            plan["reasoning_summary"].append("Query asks for a count of records.")
            return plan
    
    # Existence check
    existence_patterns = [
        r"\bis there\b", r"\bare there\b", r"\bdoes\b", 
        r"\bdo any\b", r"\bexist\b"
    ]
    for pattern in existence_patterns:
        if re.search(pattern, question):
            plan["intent"] = "exists"
            plan["reasoning_summary"].append("Query checks for existence of records.")
            return plan
    
    # Comparison
    comparison_patterns = [
        r"\bcompare\b", r"\bdifference between\b", 
        r"\bversus\b", r"\bvs\b"
    ]
    for pattern in comparison_patterns:
        if re.search(pattern, question):
            plan["intent"] = "compare"
            plan["reasoning_summary"].append("Query involves comparison between entities.")
            return plan
    
    # List/retrieve (default)
    list_patterns = [
        r"\blist\b", r"\bshow\b", r"\bdisplay\b", r"\bget\b", 
        r"\bfind\b", r"\bwhat are\b", r"\bwhich\b"
    ]
    for pattern in list_patterns:
        if re.search(pattern, question):
            plan["intent"] = "select"
            plan["reasoning_summary"].append("Query requests a list of records.")
            return plan
    
    return plan


def _detect_complexity_patterns(question: str, plan: dict) -> dict:
    """Detect patterns that indicate query complexity."""
    
    # Multi-step patterns (highest complexity)
    multi_step_patterns = [
        (r"both .+ and .+", "Query requires records matching multiple conditions (INTERSECT pattern)"),
        (r"purchased .+ and .+ genres?", "Customer purchased from multiple genres"),
        (r"bought .+ and .+", "Multiple purchase conditions"),
        (r"in .+ and .+ playlists?", "Track in multiple playlists"),
        (r"who .+ and also .+", "Multiple action conditions"),
        (r".+ as well as .+", "Dual condition pattern"),
    ]
    
    for pattern, description in multi_step_patterns:
        if re.search(pattern, question):
            plan["intersection"] = True
            plan["subquery_needed"] = True
            plan["reasoning_summary"].append(f"Complex pattern detected: {description}")
            return plan
    
    # Negation patterns
    negation_patterns = [
        (r"\bnever\b", "Exclusion via 'never'"),
        (r"\bwithout\b", "Exclusion via 'without'"),
        (r"\bnot purchased\b", "Has not purchased"),
        (r"\bno purchase\b", "No purchase records"),
        (r"\bno order\b", "No order records"),
        (r"\bno sale\b", "No sales"),
        (r"\bhaven't\b", "Exclusion pattern"),
        (r"\bhasn't\b", "Exclusion pattern"),
        (r"\bdoesn't have\b", "Doesn't have pattern"),
        (r"\bdon't have\b", "Don't have pattern"),
    ]
    
    for pattern, description in negation_patterns:
        if re.search(pattern, question):
            plan["negation"] = True
            plan["subquery_needed"] = True
            plan["reasoning_summary"].append(f"Negation detected: {description}")
            return plan
    
    return plan


def _detect_filters(question: str, plan: dict, schema: dict) -> dict:
    """Detect filter conditions in the question."""
    
    filter_patterns = [
        (r"\bwhere\b", "explicit WHERE condition"),
        (r"\bfrom\b .+", "source/location filter"),
        (r"\bafter\b", "date filter (after)"),
        (r"\bbefore\b", "date filter (before)"),
        (r"\bbetween\b", "range filter"),
        (r"\bin (\d{4})\b", "year filter"),
        (r"\bgreater than\b|\bmore than\b|\babove\b|\bover\b", "greater than (>)"),
        (r"\bless than\b|\bfewer than\b|\bbelow\b|\bunder\b", "less than (<)"),
        (r"\bequal to\b|\bexactly\b", "equality (=)"),
        (r"\blike\b|\bcontains\b|\bincludes\b", "text search (LIKE)"),
        (r"\bstarts with\b|\bbegins with\b", "prefix match"),
        (r"\bends with\b", "suffix match"),
        (r"\bby (\w+)\b", "attribute specification"),
        (r"\bfor (\w+)\b", "entity filter"),
        (r"\bcountry\b", "country filter"),
        (r"\bgenre\b", "genre filter"),
    ]
    
    detected = []
    for pattern, description in filter_patterns:
        if re.search(pattern, question):
            detected.append(description)
    
    # Check for specific value mentions
    value_patterns = [
        (r"from ([A-Z][a-z]+)", "country/location value"),
        (r'"([^"]+)"', "quoted value"),
        (r"'([^']+)'", "quoted value"),
    ]
    
    for pattern, description in value_patterns:
        match = re.search(pattern, question)
        if match:
            detected.append(f"{description}: {match.group(1)}")
    
    if detected:
        plan["filters_detected"] = True
        plan["filter_hints"] = list(set(detected))
        plan["reasoning_summary"].append(
            f"Detected filters: {', '.join(plan['filter_hints'][:3])}"
        )
    
    return plan


def _detect_aggregation(question: str, plan: dict) -> dict:
    """Detect aggregation functions."""
    
    aggregation_patterns = [
        # SUM patterns
        (r"\bsum\b|\btotal (value|amount|cost|price|revenue|sales)\b", "SUM"),
        (r"\btotal\b.*\bby\b", "SUM"),
        
        # COUNT patterns
        (r"\bcount\b|\bnumber of\b|\bhow many\b", "COUNT"),
        
        # AVERAGE patterns
        (r"\baverage\b|\bavg\b|\bmean\b", "AVG"),
        
        # MAX patterns
        (r"\bmax\b|\bmaximum\b|\bhighest\b|\blargest\b|\bbiggest\b|\bmost\b", "MAX"),
        
        # MIN patterns
        (r"\bmin\b|\bminimum\b|\blowest\b|\bsmallest\b|\bleast\b", "MIN"),
    ]
    
    for pattern, agg in aggregation_patterns:
        if re.search(pattern, question):
            plan["aggregation"] = agg
            plan["intent"] = "aggregation"
            plan["reasoning_summary"].append(f"Aggregation required: {agg}")
            break
    
    return plan


def _detect_grouping(question: str, plan: dict, schema: dict) -> dict:
    """Detect GROUP BY requirements."""
    
    group_patterns = [
        r"\bby (\w+)\b",
        r"\bper (\w+)\b",
        r"\beach (\w+)\b",
        r"\bfor each (\w+)\b",
        r"\bgrouped by (\w+)\b",
    ]
    
    # Get all tables and columns for matching
    all_identifiers = set(t.lower() for t in schema.keys())
    for info in schema.values():
        all_identifiers.update(c.lower() for c in info.get("columns", []))
    
    for pattern in group_patterns:
        matches = re.findall(pattern, question)
        for match in matches:
            if match.lower() in all_identifiers:
                plan["grouping"] = match
                plan["reasoning_summary"].append(f"Results should be grouped by '{match}'")
                break
        if plan["grouping"]:
            break
    
    return plan


def _detect_sorting_and_limits(question: str, plan: dict) -> dict:
    """Detect ORDER BY and LIMIT requirements."""
    
    # Descending order indicators
    desc_patterns = [
        r"\btop\b", r"\bhighest\b", r"\bmost\b", r"\blargest\b",
        r"\bbiggest\b", r"\bmaximum\b", r"\bbest\b", r"\bgreatest\b",
        r"\bnewest\b", r"\blatest\b", r"\brecent\b", r"\bfirst\b"
    ]
    
    # Ascending order indicators
    asc_patterns = [
        r"\bbottom\b", r"\blowest\b", r"\bleast\b", r"\bsmallest\b",
        r"\bminimum\b", r"\bworst\b", r"\boldest\b", r"\bearliest\b"
    ]
    
    for pattern in desc_patterns:
        if re.search(pattern, question):
            plan["sorting"] = "DESC"
            plan["reasoning_summary"].append("Sort order: DESCENDING")
            break
    
    if not plan["sorting"]:
        for pattern in asc_patterns:
            if re.search(pattern, question):
                plan["sorting"] = "ASC"
                plan["reasoning_summary"].append("Sort order: ASCENDING")
                break
    
    # Detect LIMIT
    limit_patterns = [
        (r"\btop\s+(\d+)\b", 1),
        (r"\bfirst\s+(\d+)\b", 1),
        (r"\blast\s+(\d+)\b", 1),
        (r"\b(\d+)\s+(?:top|best|worst|highest|lowest)\b", 1),
        (r"\blimit\s+(\d+)\b", 1),
        (r"\b(\d+)\s+results?\b", 1),
    ]
    
    for pattern, group in limit_patterns:
        match = re.search(pattern, question)
        if match:
            plan["limit"] = int(match.group(group))
            plan["reasoning_summary"].append(f"Limit to {plan['limit']} rows")
            break
    
    # Default limit for ranking queries
    if plan["sorting"] and not plan["limit"]:
        ranking_words = ["top", "best", "worst", "highest", "lowest"]
        if any(word in question for word in ranking_words):
            plan["limit"] = 10
            plan["reasoning_summary"].append("Default limit: 10 rows")
    
    return plan


def _detect_distinct(question: str, plan: dict) -> dict:
    """Detect if DISTINCT is needed."""
    
    distinct_patterns = [
        r"\bunique\b", r"\bdistinct\b", r"\bdifferent\b",
        r"\bno duplicates\b", r"\bwithout duplicates\b"
    ]
    
    for pattern in distinct_patterns:
        if re.search(pattern, question):
            plan["distinct"] = True
            plan["reasoning_summary"].append("DISTINCT required")
            break
    
    return plan


def _detect_negation(question: str, plan: dict) -> dict:
    """Detect negation patterns that require special SQL handling."""
    
    if plan["negation"]:
        return plan  # Already detected in complexity patterns
    
    negation_patterns = [
        r"\bnot\b", r"\bnever\b", r"\bno\b", r"\bwithout\b",
        r"\bexcept\b", r"\bexclude\b", r"\bmissing\b"
    ]
    
    for pattern in negation_patterns:
        if re.search(pattern, question):
            plan["negation"] = True
            plan["reasoning_summary"].append("Negation pattern detected - may need LEFT JOIN with NULL check")
            break
    
    return plan


def _detect_intersection(question: str, plan: dict) -> dict:
    """Detect intersection/multiple condition patterns."""
    
    if plan["intersection"]:
        return plan  # Already detected
    
    intersection_patterns = [
        r"\bboth\b", r"\band also\b", r"\bas well as\b",
        r"multiple", r"\ball of\b"
    ]
    
    for pattern in intersection_patterns:
        if re.search(pattern, question):
            plan["intersection"] = True
            plan["reasoning_summary"].append("Intersection pattern - may need INTERSECT or GROUP BY HAVING")
            break
    
    return plan


def _calculate_complexity(plan: dict) -> str:
    """Calculate overall query complexity."""
    
    if plan["intersection"] and plan["subquery_needed"]:
        return "multi_step"
    
    if plan["negation"] or plan["subquery_needed"]:
        return "complex"
    
    if plan["needs_join"] or plan["aggregation"] or plan["grouping"]:
        return "moderate"
    
    return "simple"


def format_plan_for_display(plan: dict) -> str:
    """Formats the plan for human-readable display."""
    
    lines = [f"📋 **Query Plan** (Complexity: {plan['complexity'].upper()})"]
    lines.append(f"• Intent: {plan['intent'].upper()}")
    lines.append(f"• Tables: {', '.join(plan['tables_considered'])}")
    
    if plan.get("aggregation"):
        lines.append(f"• Aggregation: {plan['aggregation']}")
    
    if plan.get("grouping"):
        lines.append(f"• Group By: {plan['grouping']}")
    
    if plan.get("sorting"):
        lines.append(f"• Order: {plan['sorting']}")
    
    if plan.get("limit"):
        lines.append(f"• Limit: {plan['limit']}")
    
    if plan.get("negation"):
        lines.append("• Pattern: Negation/Exclusion")
    
    if plan.get("intersection"):
        lines.append("• Pattern: Intersection (multiple conditions)")
    
    return "\n".join(lines)
