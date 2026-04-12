from pathlib import Path
from loguru import logger
from src.config import DATABASE_PATH
from src.database.connection import get_connection


def initialize_database():
    """
    Initialize the SQLite database by running schema.sql.
    Creates all tables and indexes if they don't exist.
    Safe to call multiple times.
    """
    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    with open(schema_path, 'r') as f:
        schema_sql = f.read()

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.executescript(schema_sql)
            logger.info(f"Database initialized successfully at {DATABASE_PATH}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


if __name__ == "__main__":
    initialize_database()
