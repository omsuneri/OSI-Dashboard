"""
Seed script for OSI Dashboard.
Usage: python scripts/seed.py owner/repo
Example: python scripts/seed.py sugarlabs/musicblocks
"""

import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from src.config import GITHUB_TOKEN
from src.database.init_db import initialize_database
from src.database.connection import get_connection
from src.etl.github_client import GitHubClient
from src.etl.extract import extract_repo_data
from src.etl.transform import transform_all
from src.etl.load import load_all


def seed_repository(owner: str, repo: str):
    """
    Seed the database with data from a GitHub repository.

    Args:
        owner: Repository owner username
        repo: Repository name
    """
    logger.info(f"Starting seed process for {owner}/{repo}")

    # Initialize database
    initialize_database()

    # Create GitHub client
    client = GitHubClient(token=GITHUB_TOKEN)

    try:
        # Step 1: Extract
        logger.info("Step 1: Extracting data from GitHub API...")
        raw_data = extract_repo_data(owner, repo, client)

        # Step 2: Transform
        logger.info("Step 2: Transforming data...")
        transformed_data = transform_all(raw_data)

        # Step 3: Load
        logger.info("Step 3: Loading data into database...")
        with get_connection() as conn:
            load_result = load_all(transformed_data, conn)

            logger.success(
                f"✓ Successfully seeded {owner}/{repo} (repo_id: {load_result['repo_id']})"
            )
            logger.info(f"Rows loaded: {load_result['rows_loaded']}")

        return load_result["repo_id"]

    except ValueError as e:
        logger.error(f"Repository not found: {owner}/{repo}")
        raise

    except Exception as e:
        logger.error(f"Failed to seed repository: {e}")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/seed.py owner/repo")
        print("Example: python scripts/seed.py sugarlabs/musicblocks")
        sys.exit(1)

    repo_input = sys.argv[1]

    if "/" not in repo_input:
        print("Error: Repository must be in 'owner/repo' format")
        sys.exit(1)

    owner, repo = repo_input.split("/", 1)

    try:
        repo_id = seed_repository(owner.strip(), repo.strip())
        print(f"\n✓ Success! Repository seeded with ID: {repo_id}")
        print(f"\nRun the dashboard:")
        print("  streamlit run app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
