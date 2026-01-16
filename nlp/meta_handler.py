"""
Meta-Query Handler

Handles schema introspection and meta-queries like:
- "What tables exist in this database?"
- "Show me the schema of the Invoice table"
- "Which table has the most rows?"
"""

import re
from typing import Optional, Dict, Tuple, List


def detect_meta_query(question: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Detects if a question is a meta-query about the database structure.
    
    Args:
        question: User's question
    
    Returns:
        Tuple of (is_meta_query, meta_type, target_table)
        meta_type can be: 'list_tables', 'describe_table', 'table_rows', 'table_columns', 'describe_all'
    """
    
    q = question.lower().strip()
    
    # Pattern 1: List all tables
    list_tables_patterns = [
        r"what tables",
        r"which tables",
        r"list.*tables",
        r"show.*tables",
        r"all tables",
        r"tables in.*database",
        r"database tables",
        r"available tables",
    ]
    
    for pattern in list_tables_patterns:
        if re.search(pattern, q):
            return True, "list_tables", None
    
    # Pattern 2: Describe specific table
    describe_patterns = [
        r"schema of (?:the )?(\w+)",
        r"describe (?:the )?(\w+)",
        r"structure of (?:the )?(\w+)",
        r"columns in (?:the )?(\w+)",
        r"what.*in (?:the )?(\w+) table",
        r"(\w+) table schema",
        r"(\w+) table structure",
        r"show (?:me )?(?:the )?(\w+) table",
        r"what does (?:the )?(\w+) table contain",
        r"fields in (?:the )?(\w+)",
    ]
    
    for pattern in describe_patterns:
        match = re.search(pattern, q)
        if match:
            table_name = match.group(1)
            # Filter out common words that aren't table names
            if table_name not in ['the', 'a', 'an', 'this', 'that', 'all', 'each']:
                return True, "describe_table", table_name
    
    # Pattern 3: Table with most rows
    most_rows_patterns = [
        r"which table.*most rows",
        r"largest table",
        r"biggest table",
        r"table.*most records",
        r"table.*most data",
        r"most populated table",
    ]
    
    for pattern in most_rows_patterns:
        if re.search(pattern, q):
            return True, "table_rows", None
    
    # Pattern 4: Describe all / full schema
    full_schema_patterns = [
        r"full schema",
        r"entire schema",
        r"complete schema",
        r"all columns",
        r"database structure",
        r"schema overview",
        r"describe.*database",
    ]
    
    for pattern in full_schema_patterns:
        if re.search(pattern, q):
            return True, "describe_all", None
    
    # Pattern 5: Relationships
    relationship_patterns = [
        r"relationships",
        r"foreign keys",
        r"how.*tables.*connected",
        r"table connections",
        r"links between",
    ]
    
    for pattern in relationship_patterns:
        if re.search(pattern, q):
            return True, "relationships", None
    
    return False, None, None


def handle_meta_query(
    meta_type: str,
    schema: Dict,
    target_table: Optional[str] = None
) -> Dict:
    """
    Handles a meta-query and returns the result.
    
    Args:
        meta_type: Type of meta-query
        schema: Full database schema
        target_table: Target table for describe queries
    
    Returns:
        dict with 'answer', 'data', 'columns', 'rows'
    """
    
    if meta_type == "list_tables":
        return _handle_list_tables(schema)
    
    elif meta_type == "describe_table":
        return _handle_describe_table(schema, target_table)
    
    elif meta_type == "table_rows":
        return _handle_table_rows(schema)
    
    elif meta_type == "describe_all":
        return _handle_describe_all(schema)
    
    elif meta_type == "relationships":
        return _handle_relationships(schema)
    
    return {
        "answer": "I couldn't understand that meta-query.",
        "reasoning": "Unknown meta-query type",
        "columns": [],
        "rows": []
    }


def _handle_list_tables(schema: Dict) -> Dict:
    """Lists all tables in the database."""
    
    tables = list(schema.keys())
    
    rows = []
    for table in sorted(tables):
        info = schema[table]
        col_count = len(info.get("columns", []))
        row_count = info.get("row_count", "N/A")
        rows.append([table, col_count, row_count])
    
    total_tables = len(tables)
    total_rows = sum(info.get("row_count", 0) for info in schema.values())
    
    answer = f"The database contains **{total_tables} tables** with a total of **{total_rows:,} rows**."
    
    reasoning = f"""**Schema Exploration:**
1. Scanned the database metadata
2. Found {total_tables} user tables
3. Counted columns and rows for each table
4. Tables are: {', '.join(sorted(tables))}"""
    
    return {
        "answer": answer,
        "reasoning": reasoning,
        "sql": "-- Meta-query: No SQL executed (schema introspection)",
        "columns": ["Table Name", "Columns", "Row Count"],
        "rows": rows,
        "row_count": len(rows)
    }


def _handle_describe_table(schema: Dict, target_table: Optional[str]) -> Dict:
    """Describes a specific table."""
    
    if not target_table:
        return {
            "answer": "Please specify which table you want to describe.",
            "reasoning": "No table name provided",
            "columns": [],
            "rows": []
        }
    
    # Find the table (case-insensitive)
    matched_table = None
    for table in schema.keys():
        if table.lower() == target_table.lower():
            matched_table = table
            break
    
    if not matched_table:
        # Suggest similar tables
        similar = [t for t in schema.keys() if target_table.lower() in t.lower()]
        suggestion = f" Did you mean: {', '.join(similar)}?" if similar else ""
        
        return {
            "answer": f"Table '{target_table}' not found in the database.{suggestion}",
            "reasoning": f"Searched for table '{target_table}' but it doesn't exist.",
            "columns": [],
            "rows": []
        }
    
    info = schema[matched_table]
    columns = info.get("columns", [])
    column_types = info.get("column_types", {})
    primary_keys = info.get("primary_key", [])
    foreign_keys = info.get("foreign_keys", [])
    row_count = info.get("row_count", 0)
    
    rows = []
    for col in columns:
        col_type = column_types.get(col, "UNKNOWN")
        is_pk = "✓" if col in primary_keys else ""
        
        # Check if it's a foreign key
        fk_ref = ""
        for fk in foreign_keys:
            if isinstance(fk, dict) and fk.get("from") == col:
                fk_ref = f"→ {fk['to_table']}.{fk['to_column']}"
                break
        
        rows.append([col, col_type, is_pk, fk_ref])
    
    answer = f"**{matched_table}** has **{len(columns)} columns** and **{row_count:,} rows**."
    
    reasoning = f"""**Table Analysis:**
1. Located table '{matched_table}' in schema
2. Found {len(columns)} columns
3. Primary key: {', '.join(primary_keys) if primary_keys else 'None detected'}
4. Foreign keys: {len(foreign_keys)} relationship(s)
5. Current row count: {row_count:,}"""
    
    return {
        "answer": answer,
        "reasoning": reasoning,
        "sql": f"-- Meta-query: PRAGMA table_info('{matched_table}')",
        "columns": ["Column", "Type", "Primary Key", "Foreign Key"],
        "rows": rows,
        "row_count": len(rows)
    }


def _handle_table_rows(schema: Dict) -> Dict:
    """Finds the table with the most rows."""
    
    tables_by_rows = []
    for table, info in schema.items():
        row_count = info.get("row_count", 0)
        tables_by_rows.append((table, row_count))
    
    tables_by_rows.sort(key=lambda x: x[1], reverse=True)
    
    if not tables_by_rows:
        return {
            "answer": "No tables found in the database.",
            "reasoning": "Schema is empty",
            "columns": [],
            "rows": []
        }
    
    largest = tables_by_rows[0]
    
    rows = [[table, f"{count:,}"] for table, count in tables_by_rows[:10]]
    
    answer = f"The largest table is **{largest[0]}** with **{largest[1]:,} rows**."
    
    reasoning = f"""**Row Count Analysis:**
1. Examined all {len(tables_by_rows)} tables
2. Counted rows in each table
3. Sorted by row count (descending)
4. Top table: {largest[0]} ({largest[1]:,} rows)"""
    
    return {
        "answer": answer,
        "reasoning": reasoning,
        "sql": "-- Meta-query: Row count analysis",
        "columns": ["Table", "Row Count"],
        "rows": rows,
        "row_count": len(rows)
    }


def _handle_describe_all(schema: Dict) -> Dict:
    """Provides an overview of the entire schema."""
    
    rows = []
    total_columns = 0
    total_rows = 0
    
    for table in sorted(schema.keys()):
        info = schema[table]
        columns = info.get("columns", [])
        row_count = info.get("row_count", 0)
        fk_count = len(info.get("foreign_keys", []))
        
        rows.append([
            table,
            len(columns),
            row_count,
            fk_count
        ])
        
        total_columns += len(columns)
        total_rows += row_count
    
    answer = f"Database has **{len(schema)} tables**, **{total_columns} columns**, and **{total_rows:,} total rows**."
    
    reasoning = f"""**Full Schema Overview:**
1. Analyzed complete database structure
2. Tables: {len(schema)}
3. Total columns: {total_columns}
4. Total rows: {total_rows:,}
5. Tables with relationships: {sum(1 for info in schema.values() if info.get('foreign_keys'))}"""
    
    return {
        "answer": answer,
        "reasoning": reasoning,
        "sql": "-- Meta-query: Full schema analysis",
        "columns": ["Table", "Columns", "Rows", "Foreign Keys"],
        "rows": rows,
        "row_count": len(rows)
    }


def _handle_relationships(schema: Dict) -> Dict:
    """Shows all foreign key relationships."""
    
    rows = []
    
    for table, info in schema.items():
        fks = info.get("foreign_keys", [])
        for fk in fks:
            if isinstance(fk, dict):
                rows.append([
                    table,
                    fk.get("from", ""),
                    fk.get("to_table", ""),
                    fk.get("to_column", "")
                ])
    
    if not rows:
        return {
            "answer": "No foreign key relationships found in the database.",
            "reasoning": "Scanned all tables but found no declared foreign keys.",
            "columns": [],
            "rows": []
        }
    
    answer = f"Found **{len(rows)} foreign key relationships** in the database."
    
    reasoning = f"""**Relationship Analysis:**
1. Scanned all tables for foreign key declarations
2. Found {len(rows)} relationships
3. These define how tables are connected for JOINs"""
    
    return {
        "answer": answer,
        "reasoning": reasoning,
        "sql": "-- Meta-query: Foreign key analysis",
        "columns": ["From Table", "Column", "To Table", "To Column"],
        "rows": rows,
        "row_count": len(rows)
    }
