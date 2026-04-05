"""
OSI Dashboard v3.0 — Data Analyst Edition
Main Streamlit application entry point.
"""

import streamlit as st
from datetime import datetime
from loguru import logger

from src.config import GITHUB_TOKEN
from src.database.init_db import initialize_database
from src.database.connection import get_connection
from src.etl.github_client import GitHubClient
from src.etl.extract import extract_repo_data
from src.etl.transform import transform_all
from src.etl.load import load_all
from src.dashboard.feature1_repo import render_feature1
from src.dashboard.feature2_compat import render_feature2


# Configure page
st.set_page_config(
    page_title="OSI Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database
initialize_database()

# Sidebar
st.sidebar.title("🔬 OSI Dashboard")
st.sidebar.caption("Open Source Intelligence Platform")
st.sidebar.markdown("---")

# Feature selector
feature = st.sidebar.radio(
    "Select Feature",
    ["📊 Repository Intelligence", "🎯 Compatibility Scorer"],
    key="feature_selector",
    help="Choose which analysis feature to use"
)

st.sidebar.markdown("---")

# Repository input
st.sidebar.markdown("### Repository")
repo_input = st.sidebar.text_input(
    "GitHub Repository",
    placeholder="e.g. sugarlabs/musicblocks",
    help="Enter in owner/repo format"
)

analyze_button = st.sidebar.button("🚀 Analyze", type="primary", use_container_width=True)

# Handle analysis button
if analyze_button and repo_input:
    if "/" not in repo_input:
        st.sidebar.error("⚠️ Invalid format. Use: owner/repo")
    else:
        owner, repo = repo_input.split("/", 1)
        owner = owner.strip()
        repo = repo.strip()

        with st.spinner(f"Fetching data for {owner}/{repo}..."):
            try:
                # Initialize GitHub client
                client = GitHubClient(token=GITHUB_TOKEN)

                # Check if repo already exists in DB
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, synced_at FROM repositories WHERE full_name = ?",
                        (f"{owner}/{repo}",)
                    )
                    existing = cursor.fetchone()

                    if existing:
                        repo_id = existing[0]
                        synced_at = existing[1]
                        st.sidebar.info(f"✓ Using cached data (synced: {synced_at[:10]})")
                        logger.info(f"Using existing repo_id: {repo_id}")

                        # Store in session state
                        st.session_state["repo_id"] = repo_id
                        st.session_state["full_name"] = f"{owner}/{repo}"

                    else:
                        # Extract data from GitHub
                        st.sidebar.info("📡 Fetching from GitHub API...")
                        logger.info(f"Extracting data for {owner}/{repo}")

                        raw_data = extract_repo_data(owner, repo, client)

                        # Transform data
                        st.sidebar.info("🔄 Transforming data...")
                        logger.info("Transforming data")

                        synced_at = datetime.now().isoformat()
                        transformed_data = transform_all(raw_data)

                        # Load into database
                        st.sidebar.info("💾 Loading into database...")
                        logger.info("Loading data into database")

                        with get_connection() as conn:
                            load_result = load_all(transformed_data, conn)
                            repo_id = load_result["repo_id"]

                            st.sidebar.success(
                                f"✓ Loaded {sum(load_result['rows_loaded'].values())} rows"
                            )
                            logger.info(f"Load complete: repo_id={repo_id}")

                        # Store in session state
                        st.session_state["repo_id"] = repo_id
                        st.session_state["full_name"] = f"{owner}/{repo}"

                st.rerun()

            except ValueError as e:
                st.sidebar.error(f"❌ {str(e)}")
                logger.error(f"Repository not found: {owner}/{repo}")

            except Exception as e:
                st.sidebar.error(f"❌ Error: {str(e)}")
                logger.error(f"Failed to analyze repository: {e}")

# Display feature dashboard if repo is loaded
if "repo_id" in st.session_state and "full_name" in st.session_state:
    st.sidebar.markdown("---")
    st.sidebar.success(f"✓ Analyzing: **{st.session_state['full_name']}**")

    with get_connection() as conn:
        if feature == "📊 Repository Intelligence":
            render_feature1(conn, st.session_state["repo_id"])
        else:
            render_feature2(conn, st.session_state["repo_id"])

else:
    # Welcome screen
    st.title("🔬 OSI Dashboard")
    st.markdown("### Open Source Intelligence Platform — Data Analyst Edition")

    st.markdown("---")

    st.markdown("""
    ## Welcome!

    The OSI Dashboard helps developers make **data-driven decisions** about open-source contributions.

    ### 📊 Feature 1: Repository Intelligence
    Analyze any public GitHub repository with:
    - **Contributor analytics** — Top contributors, bus factor, cohort retention
    - **PR metrics** — Merge rate, time-to-merge, size analysis
    - **Maintainer responsiveness** — Issue response time, review activity
    - **Community health** — Overall project health radar chart
    - **Good first issues** — Entry points for new contributors

    ### 🎯 Feature 2: Compatibility Scorer
    Assess your fit for a repository by:
    - **Tech stack alignment** — Match your skills to the repo's language
    - **Community culture fit** — Active community, review culture
    - **Entry barrier** — How welcoming to newcomers
    - **Time commitment match** — PR complexity vs your availability

    Get a **0-100 compatibility score** with actionable insights and next steps.

    ---

    ## Quick Start

    1. Enter a GitHub repository in the sidebar (e.g., `sugarlabs/musicblocks`)
    2. Click **🚀 Analyze**
    3. Explore the Repository Intelligence dashboard
    4. Switch to Compatibility Scorer to assess your fit

    ---

    ## Tech Stack

    - **Python** — ETL pipeline, analytics, scoring algorithm
    - **SQL (SQLite)** — Data storage with window functions, CTEs, cohort analysis
    - **Pandas** — Data transformation and analysis
    - **Plotly** — Interactive visualizations
    - **Streamlit** — Dashboard UI

    ---

    ## Sample Repositories

    Try analyzing these popular repos:
    - `microsoft/vscode` — High activity, large community
    - `facebook/react` — Very high activity, good baseline
    - `psf/requests` — Python, moderate activity, responsive maintainers
    """)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 💡 Tip")
    st.sidebar.info("Enter a GitHub repository above to get started!")


# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Built with Streamlit + Plotly + Pandas")
st.sidebar.caption("OSI Dashboard v3.0")
