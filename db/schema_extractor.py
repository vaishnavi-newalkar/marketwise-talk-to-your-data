import sqlite3

def extract_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    schema = {}
    tables = cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    for (table,) in tables:
        columns = cursor.execute(
            f'PRAGMA table_info("{table}");'
        ).fetchall()

        schema[table] = {
            "columns": [col[1] for col in columns]
        }

    conn.close()
    return schema
