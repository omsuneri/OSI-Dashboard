"""
Reset database script for OSI Dashboard.
Drops all tables and recreates the schema.
WARNING: This will delete all data!
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import DATABASE_PATH
from src.database.connection import get_connection
from src.database.init_db import initialize_database


def reset_database():
    """
    Drop all tables and recreate the database schema.
    WARNING: This deletes all data!
    """
    logger.warning("Resetting database - all data will be deleted!")

    try:
        with get_connection() as conn:
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
            """)
            tables = [row[0] for row in cursor.fetchall()]

            # Drop all tables
            for table in tables:
                logger.info(f"Dropping table: {table}")
                cursor.execute(f"DROP TABLE IF EXISTS {table}")

            conn.commit()

        logger.info("All tables dropped")

        # Recreate schema
        logger.info("Recreating schema...")
        initialize_database()

        logger.success("✓ Database reset complete")

    except Exception as e:
        logger.error(f"Failed to reset database: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE RESET WARNING")
    print("=" * 60)
    print("This will DELETE ALL DATA in the database!")
    print(f"Database: {DATABASE_PATH}")
    print("=" * 60)

    response = input("Are you sure you want to continue? (yes/no): ")

    if response.lower() == "yes":
        try:
            reset_database()
            print("\n✓ Database has been reset successfully")
            print("\nYou can now seed data:")
            print("  python scripts/seed.py owner/repo")
        except Exception as e:
            print(f"\n❌ Error: {e}")
            sys.exit(1)
    else:
        print("\n✓ Operation cancelled")
