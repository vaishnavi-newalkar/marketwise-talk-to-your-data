"""
Enhanced Schema Extractor

Extracts comprehensive schema information from SQLite databases including:
- Tables and columns
- Data types
- Primary keys
- Foreign key relationships
- Indexes
"""

import sqlite3
from typing import Dict, List, Any


def extract_schema(db_path: str) -> Dict[str, Dict[str, Any]]:
    """
    Extracts complete schema information from a SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
    
    Returns:
        dict: Schema information with structure:
            {
                "table_name": {
                    "columns": ["col1", "col2", ...],
                    "column_types": {"col1": "TEXT", ...},
                    "primary_key": ["pk_col"],
                    "foreign_keys": [
                        {
                            "from": "col",
                            "to_table": "other_table",
                            "to_column": "id"
                        }
                    ],
                    "indexes": ["index1", "index2"],
                    "row_count": 1000  # Approximate
                }
            }
    """
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    schema = {}
    
    # Get all tables (excluding system tables)
    tables = cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """).fetchall()
    
    for (table,) in tables:
        table_info = {
            "columns": [],
            "column_types": {},
            "primary_key": [],
            "foreign_keys": [],
            "indexes": [],
            "row_count": 0
        }
        
        # Get column information
        columns = cursor.execute(f'PRAGMA table_info("{table}");').fetchall()
        for col in columns:
            # col: (cid, name, type, notnull, dflt_value, pk)
            col_name = col[1]
            col_type = col[2] or "TEXT"
            is_pk = col[5] > 0
            
            table_info["columns"].append(col_name)
            table_info["column_types"][col_name] = col_type
            
            if is_pk:
                table_info["primary_key"].append(col_name)
        
        # Get foreign key information
        fks = cursor.execute(f'PRAGMA foreign_key_list("{table}");').fetchall()
        for fk in fks:
            # fk: (id, seq, table, from, to, on_update, on_delete, match)
            table_info["foreign_keys"].append({
                "from": fk[3],
                "to_table": fk[2],
                "to_column": fk[4]
            })
        
        # Get indexes
        indexes = cursor.execute(f'PRAGMA index_list("{table}");').fetchall()
        for idx in indexes:
            # idx: (seq, name, unique, origin, partial)
            if not idx[1].startswith("sqlite_"):
                table_info["indexes"].append(idx[1])
        
        # Get approximate row count (fast method)
        try:
            row_count = cursor.execute(f'SELECT COUNT(*) FROM "{table}";').fetchone()[0]
            table_info["row_count"] = row_count
        except:
            table_info["row_count"] = 0
        
        schema[table] = table_info
    
    conn.close()
    return schema


def extract_schema_summary(schema: Dict) -> str:
    """
    Creates a human-readable summary of the schema.
    
    Args:
        schema: Schema dictionary from extract_schema
    
    Returns:
        str: Formatted schema summary
    """
    lines = []
    
    for table, info in schema.items():
        columns = info.get("columns", [])
        types = info.get("column_types", {})
        pks = info.get("primary_key", [])
        fks = info.get("foreign_keys", [])
        row_count = info.get("row_count", 0)
        
        lines.append(f"📊 **{table}** ({row_count:,} rows)")
        
        # Columns with types
        col_list = []
        for col in columns:
            col_type = types.get(col, "")
            pk_marker = " 🔑" if col in pks else ""
            col_list.append(f"  • {col} ({col_type}){pk_marker}")
        lines.extend(col_list)
        
        # Foreign keys
        if fks:
            for fk in fks:
                lines.append(f"  → {fk['from']} → {fk['to_table']}.{fk['to_column']}")
        
        lines.append("")
    
    return "\n".join(lines)


def get_table_sample(db_path: str, table: str, limit: int = 5) -> List[Dict]:
    """
    Gets a sample of rows from a table.
    
    Args:
        db_path: Path to database
        table: Table name
        limit: Number of rows to retrieve
    
    Returns:
        list: List of row dictionaries
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute(f'SELECT * FROM "{table}" LIMIT ?;', (limit,))
        rows = cursor.fetchall()
        result = [dict(row) for row in rows]
    except:
        result = []
    
    conn.close()
    return result


def infer_relationships(schema: Dict) -> List[Dict]:
    """
    Infers potential relationships between tables based on column names,
    even when foreign keys are not explicitly defined.
    
    Args:
        schema: Schema dictionary
    
    Returns:
        list: Inferred relationships
    """
    relationships = []
    tables = list(schema.keys())
    
    for table in tables:
        columns = schema[table].get("columns", [])
        
        for col in columns:
            col_lower = col.lower()
            
            # Check for common FK patterns
            # Pattern 1: column_name_id
            if col_lower.endswith("_id"):
                prefix = col_lower[:-3]
                
                # Look for matching table
                for other_table in tables:
                    if other_table.lower() == prefix or \
                       other_table.lower() == prefix + "s" or \
                       other_table.lower().rstrip("s") == prefix:
                        relationships.append({
                            "from_table": table,
                            "from_column": col,
                            "to_table": other_table,
                            "to_column": "id",
                            "inferred": True
                        })
            
            # Pattern 2: table_name_column
            for other_table in tables:
                if col_lower.startswith(other_table.lower() + "_"):
                    relationships.append({
                        "from_table": table,
                        "from_column": col,
                        "to_table": other_table,
                        "to_column": col_lower.replace(other_table.lower() + "_", ""),
                        "inferred": True
                    })
    
    return relationships
