from typing import Optional
from loguru import logger
from src.etl.github_client import GitHubClient


def extract_repo_data(owner: str, repo: str, client: GitHubClient) -> dict:
    """
    Extract all relevant data from a GitHub repository.

    Args:
        owner: Repository owner username
        repo: Repository name
        client: GitHubClient instance

    Returns:
        dict with keys:
            - meta: Repository metadata
            - commits: List of commit dicts
            - pull_requests: List of PR dicts (with reviews embedded)
            - issues: List of issue dicts (true issues only, no PRs)
            - contributors: List of contributor dicts

    Raises:
        ValueError: If repository not found
        Exception: On API errors
    """
    logger.info(f"Starting data extraction for {owner}/{repo}")

    try:
        # Step 1: Fetch repository metadata
        logger.info("Step 1/5: Fetching repository metadata...")
        meta = client.get_repo_meta(owner, repo)

        # Step 2: Fetch all commits
        logger.info("Step 2/5: Fetching commits...")
        commits = client.get_commits(owner, repo)

        # Step 3: Fetch all pull requests with reviews
        logger.info("Step 3/5: Fetching pull requests...")
        pull_requests = client.get_pull_requests(owner, repo, state="all")

        # Fetch reviews for each PR
        for i, pr in enumerate(pull_requests):
            pr_number = pr["number"]
            if i < 50 or pr["state"] == "open":  # Limit reviews to first 50 PRs + all open PRs
                try:
                    reviews = client.get_pr_reviews(owner, repo, pr_number)
                    pr["reviews"] = reviews
                    pr["review_count"] = len(reviews)
                except Exception as e:
                    logger.warning(f"Failed to fetch reviews for PR #{pr_number}: {e}")
                    pr["reviews"] = []
                    pr["review_count"] = 0
            else:
                pr["reviews"] = []
                pr["review_count"] = 0

        # Step 4: Fetch all issues (true issues only)
        logger.info("Step 4/5: Fetching issues...")
        issues = client.get_issues(owner, repo, state="all")

        # Fetch first comment timestamp for response time analysis
        for i, issue in enumerate(issues):
            issue_number = issue["number"]
            if i < 100:  # Limit to first 100 issues for performance
                try:
                    comments = client.get_issue_comments(owner, repo, issue_number)
                    if comments:
                        issue["first_comment_at"] = comments[0]["created_at"]
                    else:
                        issue["first_comment_at"] = None
                except Exception as e:
                    logger.warning(f"Failed to fetch comments for issue #{issue_number}: {e}")
                    issue["first_comment_at"] = None
            else:
                issue["first_comment_at"] = None

        # Step 5: Fetch all contributors
        logger.info("Step 5/5: Fetching contributors...")
        contributors = client.get_contributors(owner, repo)

        logger.info(
            f"Extraction complete: {len(commits)} commits, {len(pull_requests)} PRs, "
            f"{len(issues)} issues, {len(contributors)} contributors"
        )

        return {
            "meta": meta,
            "commits": commits,
            "pull_requests": pull_requests,
            "issues": issues,
            "contributors": contributors,
        }

    except ValueError as e:
        logger.error(f"Repository not found: {owner}/{repo}")
        raise

    except Exception as e:
        logger.error(f"Failed to extract data for {owner}/{repo}: {e}")
        raise
