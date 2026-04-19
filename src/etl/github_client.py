import time
import requests
from typing import Optional
from loguru import logger
from src.config import GITHUB_API_BASE, DEFAULT_HEADERS


class GitHubClient:
    """
    GitHub API client with automatic rate limit handling and pagination support.
    Uses REST API v3 for fetching public repository data.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client.

        Args:
            token: Optional GitHub personal access token for higher rate limits
        """
        self.base_url = GITHUB_API_BASE
        self.headers = DEFAULT_HEADERS.copy()
        if token and token != "your_github_token_here":
            self.headers["Authorization"] = f"Bearer {token}"

    def _check_rate_limit(self, response: requests.Response):
        """
        Check rate limit from response headers and sleep if needed.

        Args:
            response: requests.Response object with rate limit headers
        """
        remaining = int(response.headers.get("X-RateLimit-Remaining", 999))
        reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))

        if remaining < 10:
            sleep_time = max(reset_timestamp - time.time(), 0) + 1
            logger.warning(
                f"Rate limit low ({remaining} remaining). "
                f"Sleeping for {sleep_time:.0f} seconds."
            )
            time.sleep(sleep_time)

    def _get(self, endpoint: str, params: dict = None) -> dict | list:
        """
        Make a GET request to the GitHub API.

        Args:
            endpoint: API endpoint path (e.g., '/repos/owner/repo')
            params: Query parameters

        Returns:
            JSON response as dict or list

        Raises:
            requests.HTTPError: On HTTP errors
        """
        url = f"{self.base_url}{endpoint}"
        params = params or {}

        try:
            response = requests.get(url, headers=self.headers, params=params)
            self._check_rate_limit(response)

            if response.status_code == 404:
                raise ValueError(f"Resource not found: {endpoint}")
            elif response.status_code == 403:
                logger.error("Rate limit exceeded or access forbidden")
                raise requests.HTTPError("GitHub API rate limit exceeded")

            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"GitHub API request failed: {endpoint} - {e}")
            raise

    def _paginate(self, endpoint: str, params: dict = None) -> list[dict]:
        """
        Fetch all pages of a paginated endpoint.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            List of all items across all pages
        """
        params = params or {}
        params["per_page"] = 100  # Max items per page
        params["page"] = 1

        all_items = []

        while True:
            try:
                items = self._get(endpoint, params)

                if not items:
                    break

                all_items.extend(items)
                logger.info(f"Fetched page {params['page']} ({len(items)} items) from {endpoint}")

                # Check if there are more pages
                if len(items) < params["per_page"]:
                    break

                params["page"] += 1

            except Exception as e:
                logger.warning(f"Pagination stopped at page {params['page']}: {e}")
                break

        return all_items

    def get_repo_meta(self, owner: str, repo: str) -> dict:
        """
        Get repository metadata.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            Repository metadata dict
        """
        logger.info(f"Fetching repo metadata: {owner}/{repo}")
        return self._get(f"/repos/{owner}/{repo}")

    def get_commits(self, owner: str, repo: str, since: Optional[str] = None) -> list[dict]:
        """
        Get all commits for a repository.

        Args:
            owner: Repository owner username
            repo: Repository name
            since: ISO 8601 timestamp to fetch commits after this date

        Returns:
            List of commit dicts
        """
        logger.info(f"Fetching commits: {owner}/{repo}")
        params = {}
        if since:
            params["since"] = since

        return self._paginate(f"/repos/{owner}/{repo}/commits", params)

    def get_pull_requests(self, owner: str, repo: str, state: str = "all") -> list[dict]:
        """
        Get all pull requests for a repository.

        Args:
            owner: Repository owner username
            repo: Repository name
            state: 'open', 'closed', or 'all'

        Returns:
            List of PR dicts
        """
        logger.info(f"Fetching pull requests: {owner}/{repo} (state={state})")
        return self._paginate(f"/repos/{owner}/{repo}/pulls", {"state": state})

    def get_pr_reviews(self, owner: str, repo: str, pr_number: int) -> list[dict]:
        """
        Get reviews for a specific pull request.

        Args:
            owner: Repository owner username
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of review dicts
        """
        return self._get(f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews")

    def get_issues(self, owner: str, repo: str, state: str = "all") -> list[dict]:
        """
        Get all issues for a repository (not including PRs).

        Args:
            owner: Repository owner username
            repo: Repository name
            state: 'open', 'closed', or 'all'

        Returns:
            List of issue dicts (PRs are filtered out)
        """
        logger.info(f"Fetching issues: {owner}/{repo} (state={state})")
        all_issues = self._paginate(f"/repos/{owner}/{repo}/issues", {"state": state})

        # GitHub Issues API returns both issues AND pull requests
        # Filter out PRs (they have a 'pull_request' key)
        true_issues = [item for item in all_issues if "pull_request" not in item]

        logger.info(f"Filtered {len(true_issues)} true issues from {len(all_issues)} items")
        return true_issues

    def get_issue_comments(self, owner: str, repo: str, issue_number: int) -> list[dict]:
        """
        Get comments for a specific issue.

        Args:
            owner: Repository owner username
            repo: Repository name
            issue_number: Issue number

        Returns:
            List of comment dicts
        """
        return self._get(f"/repos/{owner}/{repo}/issues/{issue_number}/comments")

    def get_contributors(self, owner: str, repo: str) -> list[dict]:
        """
        Get all contributors for a repository.

        Args:
            owner: Repository owner username
            repo: Repository name

        Returns:
            List of contributor dicts
        """
        logger.info(f"Fetching contributors: {owner}/{repo}")
        return self._paginate(f"/repos/{owner}/{repo}/contributors")
