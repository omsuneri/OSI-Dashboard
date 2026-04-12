import sqlite3
from contextlib import contextmanager
from src.config import DATABASE_PATH


@contextmanager
def get_connection():
    """
    Context manager for SQLite database connections.
    Ensures proper connection cleanup and error handling.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM repositories")
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
