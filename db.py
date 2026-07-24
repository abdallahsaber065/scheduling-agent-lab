import sqlite3
import os

DB_FILE = os.path.join(os.path.dirname(__file__), "database.db")

def get_db_connection():
    """Returns a SQLite connection object configured with dictionary-like row access."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query: str, args: tuple = ()) -> list[dict]:
    """Executes a SQL SELECT query safely with parameters and returns results as a list of dicts."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def execute_db(query: str, args: tuple = ()) -> int:
    """Executes a SQL INSERT/UPDATE/DELETE query and commits changes."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, args)
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
