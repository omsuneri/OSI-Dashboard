import sqlite3
import pandas as pd
from loguru import logger
from src.config import DEFAULT_DAYS_WINDOW, DEFAULT_TOP_N_CONTRIBUTORS


def get_top_contributors(
    conn: sqlite3.Connection,
    repo_id: int,
    top_n: int = DEFAULT_TOP_N_CONTRIBUTORS,
    days: int = DEFAULT_DAYS_WINDOW
) -> pd.DataFrame:
    """
    Get top contributors by commit count within a time window.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        top_n: Number of top contributors to return
        days: Time window in days

    Returns:
        DataFrame: [username, commit_count, additions, deletions, active_days, last_active]
    """
    query = """
        SELECT
            author_username,
            COUNT(*) AS commit_count,
            SUM(additions) AS additions,
            SUM(deletions) AS deletions,
            COUNT(DISTINCT DATE(committed_at)) AS active_days,
            MAX(committed_at) AS last_active
        FROM commits
        WHERE repo_id = ?
          AND committed_at >= date('now', ? || ' days')
          AND author_username IS NOT NULL
        GROUP BY author_username
        ORDER BY commit_count DESC
        LIMIT ?
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}', top_n))
        logger.info(f"Fetched {len(df)} top contributors")
        return df
    except Exception as e:
        logger.error(f"Failed to get top contributors: {e}")
        return pd.DataFrame(columns=[
            "author_username", "commit_count", "additions", "deletions",
            "active_days", "last_active"
        ])


def get_contributor_activity_over_time(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> pd.DataFrame:
    """
    Get contributor activity grouped by week.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        DataFrame: [week, username, commit_count]
    """
    query = """
        SELECT
            strftime('%Y-%W', committed_at) AS week,
            author_username AS username,
            COUNT(*) AS commit_count
        FROM commits
        WHERE repo_id = ?
          AND committed_at >= date('now', ? || ' days')
          AND author_username IS NOT NULL
        GROUP BY week, username
        ORDER BY week, commit_count DESC
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        logger.info(f"Fetched contributor activity over time: {len(df)} records")
        return df
    except Exception as e:
        logger.error(f"Failed to get contributor activity over time: {e}")
        return pd.DataFrame(columns=["week", "username", "commit_count"])


def get_contributor_retention(conn: sqlite3.Connection, repo_id: int) -> pd.DataFrame:
    """
    Cohort analysis: new contributor retention over time.
    This is the SQL showcase query demonstrating CTEs and cohort analysis.

    Args:
        conn: SQLite connection
        repo_id: Repository ID

    Returns:
        DataFrame: [cohort_month, cohort_size, active_month, active_count, retention_pct]
    """
    query = """
        WITH first_contribution AS (
            SELECT
                author_username,
                strftime('%Y-%m', MIN(committed_at)) AS cohort_month
            FROM commits
            WHERE repo_id = ? AND author_username IS NOT NULL
            GROUP BY author_username
        ),
        monthly_activity AS (
            SELECT DISTINCT
                author_username,
                strftime('%Y-%m', committed_at) AS active_month
            FROM commits
            WHERE repo_id = ? AND author_username IS NOT NULL
        )
        SELECT
            f.cohort_month,
            COUNT(DISTINCT f.author_username) AS cohort_size,
            m.active_month,
            COUNT(DISTINCT m.author_username) AS active_count,
            ROUND(100.0 * COUNT(DISTINCT m.author_username) /
                  COUNT(DISTINCT f.author_username), 1) AS retention_pct
        FROM first_contribution f
        JOIN monthly_activity m ON f.author_username = m.author_username
        GROUP BY f.cohort_month, m.active_month
        ORDER BY f.cohort_month, m.active_month
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, repo_id))
        logger.info(f"Fetched contributor retention cohort: {len(df)} records")
        return df
    except Exception as e:
        logger.error(f"Failed to get contributor retention: {e}")
        return pd.DataFrame(columns=[
            "cohort_month", "cohort_size", "active_month", "active_count", "retention_pct"
        ])


def get_bus_factor(conn: sqlite3.Connection, repo_id: int, days: int = DEFAULT_DAYS_WINDOW) -> dict:
    """
    Calculate bus factor: minimum number of contributors who together wrote > 50% of commits.
    Uses Pandas cumsum on sorted commit shares.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        dict: {'bus_factor': int, 'top_contributor_share': float}
    """
    query = """
        SELECT
            author_username,
            COUNT(*) AS commit_count,
            RANK() OVER (ORDER BY COUNT(*) DESC) AS contributor_rank,
            ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS commit_share_pct
        FROM commits
        WHERE repo_id = ?
          AND committed_at >= date('now', ? || ' days')
          AND author_username IS NOT NULL
        GROUP BY author_username
        ORDER BY contributor_rank
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))

        if df.empty:
            return {"bus_factor": 0, "top_contributor_share": 0.0}

        # Calculate cumulative share
        df["cumulative_share"] = df["commit_share_pct"].cumsum()

        # Bus factor = number of contributors needed to reach 50%
        bus_factor = len(df[df["cumulative_share"] <= 50]) + 1
        bus_factor = min(bus_factor, len(df))

        top_contributor_share = df.iloc[0]["commit_share_pct"] if not df.empty else 0.0

        logger.info(f"Bus factor: {bus_factor}, Top contributor share: {top_contributor_share}%")

        return {
            "bus_factor": bus_factor,
            "top_contributor_share": float(top_contributor_share),
        }

    except Exception as e:
        logger.error(f"Failed to calculate bus factor: {e}")
        return {"bus_factor": 0, "top_contributor_share": 0.0}
