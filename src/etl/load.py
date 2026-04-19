import sqlite3
import pandas as pd
from loguru import logger
from src.etl.transform import transform_reviews


def upsert_dataframe(
    df: pd.DataFrame,
    table: str,
    conflict_column: str,
    conn: sqlite3.Connection
) -> int:
    """
    Insert rows from DataFrame into table. On conflict, update all columns.

    Args:
        df: DataFrame to insert
        table: Target table name
        conflict_column: Column name for conflict detection (e.g., 'full_name', 'sha')
        conn: SQLite connection

    Returns:
        Number of rows inserted/updated
    """
    if df.empty:
        logger.warning(f"Empty DataFrame for table {table}, skipping insert")
        return 0

    columns = df.columns.tolist()
    placeholders = ", ".join(["?" for _ in columns])
    column_names = ", ".join(columns)

    # Build UPDATE SET clause (all columns except conflict_column)
    update_columns = [col for col in columns if col != conflict_column]
    update_set = ", ".join([f"{col} = excluded.{col}" for col in update_columns])

    sql = f"""
        INSERT INTO {table} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT({conflict_column})
        DO UPDATE SET {update_set}
    """

    cursor = conn.cursor()
    rows = [tuple(row) for row in df.values]

    try:
        cursor.executemany(sql, rows)
        affected = cursor.rowcount
        logger.info(f"Upserted {affected} rows into {table}")
        return affected
    except sqlite3.IntegrityError as e:
        logger.error(f"Integrity error inserting into {table}: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to insert into {table}: {e}")
        raise


def load_all(repo_data_transformed: dict, conn: sqlite3.Connection) -> dict:
    """
    Load all transformed data into the database in correct FK order.

    Args:
        repo_data_transformed: Dict from transform.transform_all()
        conn: SQLite connection

    Returns:
        dict: {'repo_id': int, 'rows_loaded': {table: count}}
    """
    logger.info("Starting data load...")
    rows_loaded = {}

    try:
        # Step 1: Load repository metadata
        repo_df = repo_data_transformed["repo"]
        upsert_dataframe(repo_df, "repositories", "full_name", conn)

        # Get the repo_id
        cursor = conn.cursor()
        full_name = repo_df.iloc[0]["full_name"]
        cursor.execute("SELECT id FROM repositories WHERE full_name = ?", (full_name,))
        repo_id = cursor.fetchone()[0]
        logger.info(f"Repository ID: {repo_id}")

        # Update repo_id in all DataFrames
        commits_df = repo_data_transformed["commits"].copy()
        prs_df = repo_data_transformed["pull_requests"].copy()
        issues_df = repo_data_transformed["issues"].copy()
        contributors_df = repo_data_transformed["contributors"].copy()

        if not commits_df.empty:
            commits_df["repo_id"] = repo_id
        if not prs_df.empty:
            prs_df["repo_id"] = repo_id
        if not issues_df.empty:
            issues_df["repo_id"] = repo_id
        if not contributors_df.empty:
            contributors_df["repo_id"] = repo_id

        # Step 2: Load commits first (needed for contributor dates)
        if not commits_df.empty:
            rows_loaded["commits"] = upsert_dataframe(commits_df, "commits", "sha", conn)

        # Step 3: Load contributors (after commits are loaded)
        if not contributors_df.empty:
            # Set temp values for commit dates - will update after
            contributors_df["first_commit_at"] = None
            contributors_df["last_commit_at"] = None

            rows_loaded["contributors"] = upsert_dataframe(
                contributors_df,
                "contributors",
                "repo_id, username",
                conn
            )

        # Step 4: Load pull requests
        pr_id_map = {}  # Map PR number to DB id
        if not prs_df.empty:
            rows_loaded["pull_requests"] = upsert_dataframe(
                prs_df,
                "pull_requests",
                "repo_id, pr_number",
                conn
            )

            # Get PR database IDs for reviews
            cursor.execute("SELECT id, pr_number FROM pull_requests WHERE repo_id = ?", (repo_id,))
            pr_id_map = {row[1]: row[0] for row in cursor.fetchall()}

        # Step 5: Load reviews
        reviews_count = 0
        for pr in repo_data_transformed.get("reviews_raw", []):
            # Skip None entries or non-dict entries
            if pr is None or not isinstance(pr, dict):
                continue

            pr_number = pr.get("number")
            if not pr_number or pr_number not in pr_id_map:
                continue

            pr_db_id = pr_id_map[pr_number]
            reviews = pr.get("reviews", [])

            if reviews:
                reviews_df = transform_reviews(reviews, pr_db_id, repo_id)
                if not reviews_df.empty:
                    # Reviews don't have a unique constraint, so insert directly
                    columns = reviews_df.columns.tolist()
                    placeholders = ", ".join(["?" for _ in columns])
                    column_names = ", ".join(columns)

                    sql = f"INSERT OR IGNORE INTO reviews ({column_names}) VALUES ({placeholders})"
                    rows = [tuple(row) for row in reviews_df.values]
                    cursor.executemany(sql, rows)
                    reviews_count += len(rows)

        if reviews_count > 0:
            rows_loaded["reviews"] = reviews_count
            logger.info(f"Inserted {reviews_count} reviews")

        # Step 6: Load issues
        if not issues_df.empty:
            rows_loaded["issues"] = upsert_dataframe(
                issues_df,
                "issues",
                "repo_id, issue_number",
                conn
            )

        # Update contributors with commit dates after commits are loaded
        if not commits_df.empty and not contributors_df.empty:
            cursor.execute("""
                UPDATE contributors
                SET first_commit_at = (
                    SELECT MIN(committed_at)
                    FROM commits
                    WHERE commits.repo_id = contributors.repo_id
                      AND commits.author_username = contributors.username
                ),
                last_commit_at = (
                    SELECT MAX(committed_at)
                    FROM commits
                    WHERE commits.repo_id = contributors.repo_id
                      AND commits.author_username = contributors.username
                )
                WHERE repo_id = ?
            """, (repo_id,))

        conn.commit()
        logger.info(f"Data load complete. Rows loaded: {rows_loaded}")

        return {
            "repo_id": repo_id,
            "rows_loaded": rows_loaded,
        }

    except Exception as e:
        import traceback
        conn.rollback()
        logger.error(f"Failed to load data: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
