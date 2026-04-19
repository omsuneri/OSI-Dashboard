import sqlite3
import pandas as pd
from loguru import logger
from src.config import DEFAULT_DAYS_WINDOW


def get_maintainer_activity(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> pd.DataFrame:
    """
    Get maintainer (reviewers) activity and responsiveness.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        DataFrame: [reviewer_username, review_count, approvals, changes_requested,
                   last_review_at, avg_days_to_review]
    """
    query = """
        SELECT
            r.reviewer_username,
            COUNT(*) AS review_count,
            SUM(CASE WHEN r.state = 'APPROVED' THEN 1 ELSE 0 END) AS approvals,
            SUM(CASE WHEN r.state = 'CHANGES_REQUESTED' THEN 1 ELSE 0 END) AS changes_requested,
            MAX(r.submitted_at) AS last_review_at,
            ROUND(AVG(julianday(r.submitted_at) - julianday(pr.created_at)), 1) AS avg_days_to_review
        FROM reviews r
        JOIN pull_requests pr ON r.pr_id = pr.id
        WHERE r.repo_id = ?
          AND r.submitted_at >= date('now', ? || ' days')
          AND r.reviewer_username IS NOT NULL
        GROUP BY r.reviewer_username
        ORDER BY review_count DESC
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        logger.info(f"Fetched maintainer activity: {len(df)} reviewers")
        return df
    except Exception as e:
        logger.error(f"Failed to get maintainer activity: {e}")
        return pd.DataFrame(columns=[
            "reviewer_username", "review_count", "approvals", "changes_requested",
            "last_review_at", "avg_days_to_review"
        ])


def get_issue_response_time(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> pd.DataFrame:
    """
    Get issue response time distribution.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        DataFrame: [issue_number, title, created_at, response_time_hours]
    """
    query = """
        SELECT
            issue_number,
            title,
            created_at,
            ROUND((julianday(response_at) - julianday(created_at)) * 24, 2) AS response_time_hours
        FROM issues
        WHERE repo_id = ?
          AND created_at >= date('now', ? || ' days')
          AND response_at IS NOT NULL
        ORDER BY response_time_hours
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        logger.info(f"Fetched issue response times: {len(df)} issues")
        return df
    except Exception as e:
        logger.error(f"Failed to get issue response time: {e}")
        return pd.DataFrame(columns=[
            "issue_number", "title", "created_at", "response_time_hours"
        ])


def get_issue_close_rate(conn: sqlite3.Connection, repo_id: int, days: int = DEFAULT_DAYS_WINDOW) -> dict:
    """
    Calculate issue close rate.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        dict: {'total': int, 'closed': int, 'open': int, 'close_rate': float,
               'avg_close_time_days': float}
    """
    query = """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN state = 'closed' THEN 1 ELSE 0 END) AS closed,
            SUM(CASE WHEN state = 'open' THEN 1 ELSE 0 END) AS open,
            ROUND(AVG(CASE
                WHEN state = 'closed' AND closed_at IS NOT NULL
                THEN julianday(closed_at) - julianday(created_at)
                END), 1) AS avg_close_time_days
        FROM issues
        WHERE repo_id = ?
          AND created_at >= date('now', ? || ' days')
    """

    try:
        result = pd.read_sql_query(query, conn, params=(repo_id, f'-{days}'))
        total = int(result.iloc[0]["total"]) if not result.empty else 0
        closed = int(result.iloc[0]["closed"]) if not result.empty else 0
        open_count = int(result.iloc[0]["open"]) if not result.empty else 0
        avg_close_days = float(result.iloc[0]["avg_close_time_days"]) if not result.empty and result.iloc[0]["avg_close_time_days"] else 0.0

        close_rate = (closed / total * 100) if total > 0 else 0.0

        logger.info(f"Issue close rate: {close_rate:.1f}% ({closed}/{total})")

        return {
            "total": total,
            "closed": closed,
            "open": open_count,
            "close_rate": close_rate,
            "avg_close_time_days": avg_close_days,
        }

    except Exception as e:
        logger.error(f"Failed to get issue close rate: {e}")
        return {
            "total": 0,
            "closed": 0,
            "open": 0,
            "close_rate": 0.0,
            "avg_close_time_days": 0.0,
        }


def get_maintainer_responsiveness_score(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> float:
    """
    Calculate composite maintainer responsiveness score (0-100).

    Scoring components:
    - Avg issue response time (0-40 pts): < 24hrs = 40, < 72hrs = 30, < 168hrs = 20, else 10
    - PR review coverage (0-30 pts): % of PRs with at least 1 review
    - Avg time to first review (0-30 pts): < 24hrs = 30, < 72hrs = 20, < 168hrs = 10, else 5

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        float: Responsiveness score (0-100)
    """
    score = 0.0

    # Component 1: Issue response time (0-40 pts)
    try:
        issue_response_query = """
            SELECT AVG(julianday(response_at) - julianday(created_at)) * 24 AS avg_response_hours
            FROM issues
            WHERE repo_id = ?
              AND created_at >= date('now', ? || ' days')
              AND response_at IS NOT NULL
        """
        result = pd.read_sql_query(issue_response_query, conn, params=(repo_id, f'-{days}'))
        avg_response_hours = float(result.iloc[0]["avg_response_hours"]) if not result.empty and result.iloc[0]["avg_response_hours"] else 9999

        if avg_response_hours < 24:
            score += 40
        elif avg_response_hours < 72:
            score += 30
        elif avg_response_hours < 168:
            score += 20
        else:
            score += 10

    except Exception as e:
        logger.warning(f"Failed to calculate issue response time score: {e}")
        score += 10  # Default low score

    # Component 2: PR review coverage (0-30 pts)
    try:
        review_coverage_query = """
            SELECT
                ROUND(100.0 * SUM(CASE WHEN review_count > 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS coverage_pct
            FROM pull_requests
            WHERE repo_id = ?
              AND created_at >= date('now', ? || ' days')
        """
        result = pd.read_sql_query(review_coverage_query, conn, params=(repo_id, f'-{days}'))
        coverage_pct = float(result.iloc[0]["coverage_pct"]) if not result.empty and result.iloc[0]["coverage_pct"] else 0.0

        score += (coverage_pct / 100) * 30

    except Exception as e:
        logger.warning(f"Failed to calculate PR review coverage: {e}")

    # Component 3: Avg time to first review (0-30 pts)
    try:
        first_review_query = """
            SELECT
                AVG(julianday(r.submitted_at) - julianday(pr.created_at)) * 24 AS avg_hours_to_review
            FROM pull_requests pr
            JOIN (
                SELECT pr_id, MIN(submitted_at) AS submitted_at
                FROM reviews
                GROUP BY pr_id
            ) r ON pr.id = r.pr_id
            WHERE pr.repo_id = ?
              AND pr.created_at >= date('now', ? || ' days')
        """
        result = pd.read_sql_query(first_review_query, conn, params=(repo_id, f'-{days}'))
        avg_hours = float(result.iloc[0]["avg_hours_to_review"]) if not result.empty and result.iloc[0]["avg_hours_to_review"] else 9999

        if avg_hours < 24:
            score += 30
        elif avg_hours < 72:
            score += 20
        elif avg_hours < 168:
            score += 10
        else:
            score += 5

    except Exception as e:
        logger.warning(f"Failed to calculate time to first review: {e}")
        score += 5  # Default low score

    logger.info(f"Maintainer responsiveness score: {score:.1f}/100")
    return round(score, 1)
