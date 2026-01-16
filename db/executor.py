import sqlite3

def execute_sql(db_path, sql):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    rows = cursor.execute(sql).fetchall()
    conn.close()
    return rows
