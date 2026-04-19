import sqlite3
import pandas as pd
from loguru import logger
from src.config import DEFAULT_DAYS_WINDOW, DEFAULT_GOOD_FIRST_ISSUES_LIMIT
from src.analytics.pr_analytics import get_pr_merge_rate, get_pr_merge_time_distribution
from src.analytics.maintainer_analytics import get_maintainer_responsiveness_score
from src.analytics.contributor_analytics import get_bus_factor


def get_community_health_summary(
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = DEFAULT_DAYS_WINDOW
) -> dict:
    """
    Aggregate all community health signals into a single summary dict.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        dict with health metrics
    """
    try:
        # Merge rate
        pr_merge_data = get_pr_merge_rate(conn, repo_id, days)
        merge_rate = pr_merge_data["merge_rate"]

        # Avg merge time
        merge_times = get_pr_merge_time_distribution(conn, repo_id, days)
        avg_merge_time_days = merge_times["merge_time_days"].mean() if not merge_times.empty else 0.0

        # Maintainer responsiveness
        responsiveness = get_maintainer_responsiveness_score(conn, repo_id, days)

        # Bus factor
        bus_data = get_bus_factor(conn, repo_id, days)
        bus_factor = bus_data["bus_factor"]

        # Commit frequency (commits per week)
        commit_freq_query = """
            SELECT COUNT(*) * 7.0 / ? AS commits_per_week
            FROM commits
            WHERE repo_id = ?
              AND committed_at >= date('now', ? || ' days')
        """
        result = pd.read_sql_query(commit_freq_query, conn, params=(days, repo_id, f'-{days}'))
        commit_frequency = float(result.iloc[0]["commits_per_week"]) if not result.empty else 0.0

        # Good first issues count
        good_first_query = """
            SELECT COUNT(*) AS count
            FROM issues
            WHERE repo_id = ?
              AND state = 'open'
              AND (labels LIKE '%good first issue%'
                   OR labels LIKE '%beginner%'
                   OR labels LIKE '%easy%'
                   OR labels LIKE '%help wanted%')
        """
        result = pd.read_sql_query(good_first_query, conn, params=(repo_id,))
        good_first_count = int(result.iloc[0]["count"]) if not result.empty else 0

        # Open issue count
        open_issue_query = """
            SELECT COUNT(*) AS count
            FROM issues
            WHERE repo_id = ? AND state = 'open'
        """
        result = pd.read_sql_query(open_issue_query, conn, params=(repo_id,))
        open_issue_count = int(result.iloc[0]["count"]) if not result.empty else 0

        # PR comment average
        pr_comment_query = """
            SELECT AVG(comment_count) AS avg_comments
            FROM pull_requests
            WHERE repo_id = ?
              AND created_at >= date('now', ? || ' days')
        """
        result = pd.read_sql_query(pr_comment_query, conn, params=(repo_id, f'-{days}'))
        avg_pr_comments = float(result.iloc[0]["avg_comments"]) if not result.empty and result.iloc[0]["avg_comments"] else 0.0

        summary = {
            "merge_rate": round(merge_rate, 1),
            "avg_merge_time_days": round(avg_merge_time_days, 1),
            "maintainer_responsiveness": responsiveness,
            "bus_factor": bus_factor,
            "commit_frequency_per_week": round(commit_frequency, 1),
            "good_first_issues_count": good_first_count,
            "open_issue_count": open_issue_count,
            "pr_comment_avg": round(avg_pr_comments, 1),
        }

        logger.info(f"Community health summary: {summary}")
        return summary

    except Exception as e:
        logger.error(f"Failed to get community health summary: {e}")
        return {
            "merge_rate": 0.0,
            "avg_merge_time_days": 0.0,
            "maintainer_responsiveness": 0.0,
            "bus_factor": 0,
            "commit_frequency_per_week": 0.0,
            "good_first_issues_count": 0,
            "open_issue_count": 0,
            "pr_comment_avg": 0.0,
        }


def get_good_first_issues(
    conn: sqlite3.Connection,
    repo_id: int,
    limit: int = DEFAULT_GOOD_FIRST_ISSUES_LIMIT
) -> pd.DataFrame:
    """
    Get open issues labeled as beginner-friendly.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        limit: Maximum number of issues to return

    Returns:
        DataFrame: [issue_number, title, created_at, comment_count, labels]
    """
    query = """
        SELECT
            issue_number,
            title,
            created_at,
            comment_count,
            labels
        FROM issues
        WHERE repo_id = ?
          AND state = 'open'
          AND (labels LIKE '%good first issue%'
               OR labels LIKE '%beginner%'
               OR labels LIKE '%easy%'
               OR labels LIKE '%help wanted%'
               OR labels LIKE '%good-first-issue%')
        ORDER BY created_at DESC
        LIMIT ?
    """

    try:
        df = pd.read_sql_query(query, conn, params=(repo_id, limit))
        logger.info(f"Fetched {len(df)} good first issues")
        return df
    except Exception as e:
        logger.error(f"Failed to get good first issues: {e}")
        return pd.DataFrame(columns=[
            "issue_number", "title", "created_at", "comment_count", "labels"
        ])


def get_weekly_activity_trend(conn: sqlite3.Connection, repo_id: int, weeks: int = 12) -> pd.DataFrame:
    """
    Get combined weekly activity trend (commits + PRs + issues).

    Args:
        conn: SQLite connection
        repo_id: Repository ID
        weeks: Number of weeks to look back

    Returns:
        DataFrame: [week, commit_count, pr_count, issue_count]
    """
    days = weeks * 7

    query = """
        WITH weeks AS (
            SELECT DISTINCT strftime('%Y-%W', committed_at) AS week
            FROM commits
            WHERE repo_id = ? AND committed_at >= date('now', ? || ' days')
        ),
        commit_counts AS (
            SELECT
                strftime('%Y-%W', committed_at) AS week,
                COUNT(*) AS commit_count
            FROM commits
            WHERE repo_id = ? AND committed_at >= date('now', ? || ' days')
            GROUP BY week
        ),
        pr_counts AS (
            SELECT
                strftime('%Y-%W', created_at) AS week,
                COUNT(*) AS pr_count
            FROM pull_requests
            WHERE repo_id = ? AND created_at >= date('now', ? || ' days')
            GROUP BY week
        ),
        issue_counts AS (
            SELECT
                strftime('%Y-%W', created_at) AS week,
                COUNT(*) AS issue_count
            FROM issues
            WHERE repo_id = ? AND created_at >= date('now', ? || ' days')
            GROUP BY week
        )
        SELECT
            w.week,
            COALESCE(cc.commit_count, 0) AS commit_count,
            COALESCE(pc.pr_count, 0) AS pr_count,
            COALESCE(ic.issue_count, 0) AS issue_count
        FROM weeks w
        LEFT JOIN commit_counts cc ON w.week = cc.week
        LEFT JOIN pr_counts pc ON w.week = pc.week
        LEFT JOIN issue_counts ic ON w.week = ic.week
        ORDER BY w.week
    """

    try:
        df = pd.read_sql_query(
            query,
            conn,
            params=(repo_id, f'-{days}', repo_id, f'-{days}', repo_id, f'-{days}', repo_id, f'-{days}')
        )
        logger.info(f"Fetched weekly activity trend: {len(df)} weeks")
        return df
    except Exception as e:
        logger.error(f"Failed to get weekly activity trend: {e}")
        return pd.DataFrame(columns=["week", "commit_count", "pr_count", "issue_count"])
