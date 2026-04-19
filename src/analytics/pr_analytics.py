import sqlite3
import pandas as pd
from loguru import logger
from src.config import DEFAULT_DAYS_WINDOW


def get_pr_merge_rate(conn: sqlite3.Connection, repo_id: int, days: int = DEFAULT_DAYS_WINDOW) -> dict:
    """
    Calculate PR merge rate.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        dict: {'total': int, 'merged': int, 'rejected': int, 'merge_rate': float}
    """
    query = """
        SELECT
            COUNT(*) AS total,
            SUM(is_merged) AS merged,
            SUM(CASE WHEN state = 'closed' AND is_merged = 0 THEN 1 ELSE 0 END) AS rejected
        FROM pull_requests
        WHERE repo_id = ?
          AND created_at >= date('now', ? || ' days')
          AND state = 'closed'
    """

    try:
        result = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        total = int(result.iloc[0]["total"]) if not result.empty else 0
        merged = int(result.iloc[0]["merged"]) if not result.empty else 0
        rejected = int(result.iloc[0]["rejected"]) if not result.empty else 0

        merge_rate = (merged / total * 100) if total > 0 else 0.0

        logger.info(f"PR merge rate: {merge_rate:.1f}% ({merged}/{total})")

        return {
            "total": total,
            "merged": merged,
            "rejected": rejected,
            "merge_rate": merge_rate,
        }

    except Exception as e:
        logger.error(f"Failed to get PR merge rate: {e}")
        return {"total": 0, "merged": 0, "rejected": 0, "merge_rate": 0.0}


def get_pr_merge_time_distribution(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> pd.DataFrame:
    """
    Get merge time distribution for merged PRs.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        DataFrame: [pr_number, title, author, merge_time_hours, merge_time_days]
    """
    query = """
        SELECT
            pr_number,
            title,
            author_username AS author,
            ROUND((julianday(merged_at) - julianday(created_at)) * 24, 2) AS merge_time_hours,
            ROUND(julianday(merged_at) - julianday(created_at), 2) AS merge_time_days
        FROM pull_requests
        WHERE repo_id = ?
          AND is_merged = 1
          AND merged_at IS NOT NULL
          AND created_at >= date('now', ? || ' days')
        ORDER BY merge_time_hours
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        logger.info(f"Fetched merge time distribution: {len(df)} PRs")
        return df
    except Exception as e:
        logger.error(f"Failed to get PR merge time distribution: {e}")
        return pd.DataFrame(columns=[
            "pr_number", "title", "author", "merge_time_hours", "merge_time_days"
        ])


def get_pr_activity_over_time(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> pd.DataFrame:
    """
    Get PR activity (opened, merged, rejected) grouped by week.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        DataFrame: [week, prs_opened, prs_merged, prs_rejected]
    """
    query = """
        SELECT
            strftime('%Y-%W', created_at) AS week,
            COUNT(*) AS prs_opened,
            SUM(is_merged) AS prs_merged,
            SUM(CASE WHEN state = 'closed' AND is_merged = 0 THEN 1 ELSE 0 END) AS prs_rejected
        FROM pull_requests
        WHERE repo_id = ?
          AND created_at >= date('now', ? || ' days')
        GROUP BY week
        ORDER BY week
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        logger.info(f"Fetched PR activity over time: {len(df)} weeks")
        return df
    except Exception as e:
        logger.error(f"Failed to get PR activity over time: {e}")
        return pd.DataFrame(columns=["week", "prs_opened", "prs_merged", "prs_rejected"])


def get_pr_size_analysis(conn: sqlite3.Connection, repo_id: int) -> pd.DataFrame:
    """
    Analyze PRs by size bucket (XS, S, M, L, XL) with merge rates.
    Showcases SQL CASE statements and aggregation.

    Args:
        conn: SQLite connection
        repo_id: Repository ID

    Returns:
        DataFrame: [size_bucket, total_prs, merged_prs, merge_rate_pct, avg_merge_hours]
    """
    query = """
        SELECT
            CASE
                WHEN (additions + deletions) < 50   THEN 'XS (< 50 lines)'
                WHEN (additions + deletions) < 200  THEN 'S (50-200)'
                WHEN (additions + deletions) < 500  THEN 'M (200-500)'
                WHEN (additions + deletions) < 1000 THEN 'L (500-1000)'
                ELSE 'XL (1000+)'
            END AS size_bucket,
            COUNT(*) AS total_prs,
            SUM(is_merged) AS merged_prs,
            ROUND(100.0 * SUM(is_merged) / COUNT(*), 1) AS merge_rate_pct,
            ROUND(AVG(CASE
                WHEN is_merged = 1
                THEN (julianday(merged_at) - julianday(created_at)) * 24
                END), 1) AS avg_merge_hours
        FROM pull_requests
        WHERE repo_id = ? AND state = 'closed'
        GROUP BY size_bucket
        ORDER BY MIN(additions + deletions)
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id,))
        logger.info(f"Fetched PR size analysis: {len(df)} buckets")
        return df
    except Exception as e:
        logger.error(f"Failed to get PR size analysis: {e}")
        return pd.DataFrame(columns=[
            "size_bucket", "total_prs", "merged_prs", "merge_rate_pct", "avg_merge_hours"
        ])


def get_first_time_contributor_prs(conn: sqlite3.Connection, repo_id: int) -> dict:
    """
    Identify PRs by first-time contributors and their merge rate.

    Args:
        conn: SQLite connection
        repo_id: Repository ID

    Returns:
        dict: {'first_time_pr_count': int, 'first_time_merge_rate': float}
    """
    query = """
        WITH contributor_first_pr AS (
            SELECT
                author_username,
                MIN(created_at) AS first_pr_date,
                MIN(pr_number) AS first_pr_number
            FROM pull_requests
            WHERE repo_id = ?
            GROUP BY author_username
        )
        SELECT
            COUNT(*) AS first_time_pr_count,
            ROUND(100.0 * SUM(pr.is_merged) / COUNT(*), 1) AS first_time_merge_rate
        FROM pull_requests pr
        JOIN contributor_first_pr cfp
            ON pr.author_username = cfp.author_username
            AND pr.pr_number = cfp.first_pr_number
        WHERE pr.repo_id = ?
    """

    try:
        result = pd.read_sql_query(query, conn, params=(repo_id, repo_id))
        count = int(result.iloc[0]["first_time_pr_count"]) if not result.empty else 0
        merge_rate = float(result.iloc[0]["first_time_merge_rate"]) if not result.empty else 0.0

        logger.info(f"First-time contributor PRs: {count}, Merge rate: {merge_rate}%")

        return {
            "first_time_pr_count": count,
            "first_time_merge_rate": merge_rate,
        }

    except Exception as e:
        logger.error(f"Failed to get first-time contributor PRs: {e}")
        return {"first_time_pr_count": 0, "first_time_merge_rate": 0.0}
