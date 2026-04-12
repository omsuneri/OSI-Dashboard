import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Optional but recommended
DATABASE_PATH = str(DATA_DIR / "osi_dashboard.db")
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

GITHUB_API_BASE = "https://api.github.com"
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
if GITHUB_TOKEN and GITHUB_TOKEN != "your_github_token_here":
    DEFAULT_HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"

# Analysis defaults
DEFAULT_DAYS_WINDOW = 90
DEFAULT_TOP_N_CONTRIBUTORS = 10
DEFAULT_GOOD_FIRST_ISSUES_LIMIT = 20
