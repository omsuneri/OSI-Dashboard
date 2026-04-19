import json
from datetime import datetime
import pandas as pd
from loguru import logger


def transform_repo_meta(raw: dict, synced_at: str = None) -> pd.DataFrame:
    """
    Transform repository metadata into a DataFrame.

    Args:
        raw: Raw repository metadata dict from GitHub API
        synced_at: ISO timestamp of when data was synced (defaults to now)

    Returns:
        1-row DataFrame with repository fields
    """
    if synced_at is None:
        synced_at = datetime.now().isoformat()

    data = {
        "owner": raw.get("owner", {}).get("login", ""),
        "name": raw.get("name", ""),
        "full_name": raw.get("full_name", ""),
        "description": raw.get("description", ""),
        "primary_language": raw.get("language", ""),
        "stars": raw.get("stargazers_count", 0),
        "forks": raw.get("forks_count", 0),
        "open_issues": raw.get("open_issues_count", 0),
        "created_at": raw.get("created_at", ""),
        "synced_at": synced_at,
    }

    return pd.DataFrame([data])


def transform_commits(raw_commits: list, repo_id: int) -> pd.DataFrame:
    """
    Transform raw commits into a DataFrame.

    Args:
        raw_commits: List of commit dicts from GitHub API
        repo_id: Database ID of the repository

    Returns:
        DataFrame with columns: [repo_id, sha, author_username, author_email,
                                  message, committed_at, additions, deletions, files_changed]
    """
    if not raw_commits:
        return pd.DataFrame(columns=[
            "repo_id", "sha", "author_username", "author_email", "message",
            "committed_at", "additions", "deletions", "files_changed"
        ])

    transformed = []

    for commit in raw_commits:
        commit_data = commit.get("commit", {})
        author_info = commit.get("author") or {}
        commit_author = commit_data.get("author", {})
        stats = commit.get("stats", {})

        transformed.append({
            "repo_id": repo_id,
            "sha": commit.get("sha", ""),
            "author_username": author_info.get("login") or commit_author.get("name", ""),
            "author_email": commit_author.get("email", ""),
            "message": commit_data.get("message", ""),
            "committed_at": commit_data.get("author", {}).get("date", ""),
            "additions": stats.get("additions", 0),
            "deletions": stats.get("deletions", 0),
            "files_changed": stats.get("total", 0),
        })

    df = pd.DataFrame(transformed)
    logger.info(f"Transformed {len(df)} commits")
    return df


def transform_pull_requests(raw_prs: list, repo_id: int) -> pd.DataFrame:
    """
    Transform raw pull requests into a DataFrame.

    Args:
        raw_prs: List of PR dicts from GitHub API
        repo_id: Database ID of the repository

    Returns:
        DataFrame with columns: [repo_id, pr_number, title, author_username, state,
                                 is_merged, created_at, merged_at, closed_at,
                                 additions, deletions, review_count, comment_count, labels]
    """
    if not raw_prs:
        return pd.DataFrame(columns=[
            "repo_id", "pr_number", "title", "author_username", "state",
            "is_merged", "created_at", "merged_at", "closed_at",
            "additions", "deletions", "review_count", "comment_count", "labels"
        ])

    transformed = []

    for pr in raw_prs:
        labels = [label["name"] for label in pr.get("labels", [])]

        transformed.append({
            "repo_id": repo_id,
            "pr_number": pr.get("number", 0),
            "title": pr.get("title", ""),
            "author_username": pr.get("user", {}).get("login", ""),
            "state": pr.get("state", ""),
            "is_merged": 1 if pr.get("merged_at") else 0,
            "created_at": pr.get("created_at", ""),
            "merged_at": pr.get("merged_at"),
            "closed_at": pr.get("closed_at"),
            "additions": pr.get("additions", 0),
            "deletions": pr.get("deletions", 0),
            "review_count": pr.get("review_count", 0),
            "comment_count": pr.get("comments", 0),
            "labels": json.dumps(labels),
        })

    df = pd.DataFrame(transformed)
    logger.info(f"Transformed {len(df)} pull requests")
    return df


def transform_reviews(raw_reviews: list, pr_db_id: int, repo_id: int) -> pd.DataFrame:
    """
    Transform raw PR reviews into a DataFrame.

    Args:
        raw_reviews: List of review dicts from GitHub API
        pr_db_id: Database ID of the pull request
        repo_id: Database ID of the repository

    Returns:
        DataFrame with columns: [pr_id, repo_id, reviewer_username, state, submitted_at]
    """
    if not raw_reviews:
        return pd.DataFrame(columns=[
            "pr_id", "repo_id", "reviewer_username", "state", "submitted_at"
        ])

    transformed = []

    for review in raw_reviews:
        # Skip None or invalid review entries
        if review is None or not isinstance(review, dict):
            continue

        # Skip reviews without a user (can happen with deleted accounts)
        user = review.get("user")
        if user is None:
            continue

        transformed.append({
            "pr_id": pr_db_id,
            "repo_id": repo_id,
            "reviewer_username": user.get("login", ""),
            "state": review.get("state", ""),
            "submitted_at": review.get("submitted_at", ""),
        })

    return pd.DataFrame(transformed)


def transform_issues(raw_issues: list, repo_id: int) -> pd.DataFrame:
    """
    Transform raw issues into a DataFrame.

    Args:
        raw_issues: List of issue dicts from GitHub API (PRs already filtered out)
        repo_id: Database ID of the repository

    Returns:
        DataFrame with columns: [repo_id, issue_number, title, author_username, state,
                                 created_at, closed_at, response_at, labels, comment_count]
    """
    if not raw_issues:
        return pd.DataFrame(columns=[
            "repo_id", "issue_number", "title", "author_username", "state",
            "created_at", "closed_at", "response_at", "labels", "comment_count"
        ])

    transformed = []

    for issue in raw_issues:
        # Skip if it's a PR (shouldn't happen, but double-check)
        if "pull_request" in issue:
            continue

        labels = [label["name"] for label in issue.get("labels", [])]

        transformed.append({
            "repo_id": repo_id,
            "issue_number": issue.get("number", 0),
            "title": issue.get("title", ""),
            "author_username": issue.get("user", {}).get("login", ""),
            "state": issue.get("state", ""),
            "created_at": issue.get("created_at", ""),
            "closed_at": issue.get("closed_at"),
            "response_at": issue.get("first_comment_at"),
            "labels": json.dumps(labels),
            "comment_count": issue.get("comments", 0),
        })

    df = pd.DataFrame(transformed)
    logger.info(f"Transformed {len(df)} issues")
    return df


def transform_contributors(raw_contributors: list, repo_id: int) -> pd.DataFrame:
    """
    Transform raw contributors into a DataFrame.

    Args:
        raw_contributors: List of contributor dicts from GitHub API
        repo_id: Database ID of the repository

    Returns:
        DataFrame with columns: [repo_id, username, avatar_url, total_commits]
    """
    if not raw_contributors:
        return pd.DataFrame(columns=[
            "repo_id", "username", "avatar_url", "total_commits"
        ])

    transformed = []

    for contributor in raw_contributors:
        transformed.append({
            "repo_id": repo_id,
            "username": contributor.get("login", ""),
            "avatar_url": contributor.get("avatar_url", ""),
            "total_commits": contributor.get("contributions", 0),
        })

    df = pd.DataFrame(transformed)
    logger.info(f"Transformed {len(df)} contributors")
    return df


def transform_all(raw_data: dict, repo_id: int = None) -> dict:
    """
    Transform all extracted data into DataFrames.

    Args:
        raw_data: Dict from extract.extract_repo_data() with keys:
                  {meta, commits, pull_requests, issues, contributors}
        repo_id: Optional repo_id if already known (otherwise extracted from meta)

    Returns:
        Dict of DataFrames: {
            'repo': DataFrame,
            'commits': DataFrame,
            'pull_requests': DataFrame,
            'issues': DataFrame,
            'contributors': DataFrame,
            'reviews': list[DataFrame]  # One per PR
        }
    """
    logger.info("Starting data transformation...")

    # Transform repository metadata
    repo_df = transform_repo_meta(raw_data["meta"])

    # If repo_id provided, use it. Otherwise it will be assigned during load
    if repo_id:
        commits_df = transform_commits(raw_data["commits"], repo_id)
        prs_df = transform_pull_requests(raw_data["pull_requests"], repo_id)
        issues_df = transform_issues(raw_data["issues"], repo_id)
        contributors_df = transform_contributors(raw_data["contributors"], repo_id)
    else:
        # Will assign repo_id during load phase
        commits_df = transform_commits(raw_data["commits"], -1)
        prs_df = transform_pull_requests(raw_data["pull_requests"], -1)
        issues_df = transform_issues(raw_data["issues"], -1)
        contributors_df = transform_contributors(raw_data["contributors"], -1)

    logger.info("Transformation complete")

    return {
        "repo": repo_df,
        "commits": commits_df,
        "pull_requests": prs_df,
        "issues": issues_df,
        "contributors": contributors_df,
        "reviews_raw": raw_data["pull_requests"],  # Keep for reviews extraction after PR load
    }
