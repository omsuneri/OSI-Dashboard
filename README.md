# OSI Dashboard — Open Source Intelligence Platform

> **Data Analyst Edition v3.0**
> A data-driven tool for developers to analyze GitHub repositories and assess their contribution compatibility.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.35+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 🎯 Project Overview

The OSI Dashboard is a comprehensive analytics platform that helps developers make **informed decisions** about open-source contributions. It combines GitHub API data extraction, SQL analytics, and interactive visualizations to provide actionable insights.

### ✨ Features

#### 📊 Feature 1: Repository Intelligence Dashboard
Analyze any public GitHub repository with comprehensive metrics:
- **Contributor Analytics** — Top contributors, bus factor, cohort retention analysis
- **PR Metrics** — Merge rate, time-to-merge distribution, size analysis
- **Maintainer Responsiveness** — Issue response time, review activity, close rates
- **Community Health** — Multi-dimensional radar chart with health indicators
- **Good First Issues** — Beginner-friendly entry points

#### 🎯 Feature 2: Contributor Compatibility Scorer
Get a personalized 0-100 compatibility score by:
- **Tech Stack Alignment** — Match your skills to the repo's language profile
- **Community Culture Fit** — Activity level, review culture assessment
- **Entry Barrier Analysis** — How welcoming to first-time contributors
- **Time Commitment Match** — PR complexity vs. your availability

Receive a detailed breakdown with strengths, concerns, and actionable next steps.

---

## 🛠️ Tech Stack

### Core Technologies
- **Python 3.11+** — Data pipeline and analytics
- **SQL (SQLite)** — Normalized schema with advanced queries
- **Pandas** — Data transformation and analysis
- **Plotly** — Interactive visualizations
- **Streamlit** — Dashboard UI

### Key SQL Features Demonstrated
- Window functions (`RANK()`, `OVER()`)
- Common Table Expressions (CTEs)
- Cohort retention analysis
- Complex JOINs and aggregations
- Date/time calculations with `julianday()` and `strftime()`

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- GitHub Personal Access Token (optional, for higher rate limits)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/osi-dashboard-v3
cd osi-dashboard-v3

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional)
cp .env.example .env
# Edit .env and add your GITHUB_TOKEN
```

### Running the Dashboard

```bash
# Start the Streamlit app
streamlit run app.py
```

The dashboard will open at `http://localhost:8501`

### Seeding Data (Optional)

You can pre-seed data for faster analysis:

```bash
# Seed a specific repository
python scripts/seed.py sugarlabs/musicblocks

# Or analyze multiple repos
python scripts/seed.py microsoft/vscode
python scripts/seed.py facebook/react
python scripts/seed.py psf/requests
```

### Resetting the Database

```bash
# WARNING: This deletes all data!
python scripts/reset_db.py
```

---

## 📁 Project Structure

```
osi-dashboard-v3/
├── app.py                        # Streamlit entry point
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (not committed)
├── .gitignore
│
├── data/
│   └── osi_dashboard.db          # SQLite database (auto-created)
│
├── src/
│   ├── config.py                 # Configuration and constants
│   │
│   ├── database/
│   │   ├── schema.sql            # Database schema (all CREATE TABLE statements)
│   │   ├── init_db.py            # Initialize database
│   │   └── connection.py         # Database connection manager
│   │
│   ├── etl/
│   │   ├── github_client.py      # GitHub API wrapper with rate limiting
│   │   ├── extract.py            # Extract data from GitHub API
│   │   ├── transform.py          # Transform into Pandas DataFrames
│   │   └── load.py               # Load into SQLite database
│   │
│   ├── analytics/
│   │   ├── contributor_analytics.py    # Contributor metrics
│   │   ├── pr_analytics.py             # Pull request analytics
│   │   ├── maintainer_analytics.py     # Maintainer responsiveness
│   │   ├── health_analytics.py         # Community health metrics
│   │   └── compatibility_scorer.py     # Compatibility scoring algorithm
│   │
│   └── dashboard/
│       ├── components.py         # Reusable UI components
│       ├── feature1_repo.py      # Repository Intelligence dashboard
│       └── feature2_compat.py    # Compatibility Scorer dashboard
│
└── scripts/
    ├── seed.py                   # Seed database with repo data
    └── reset_db.py               # Reset database (drops all tables)
```

---

## 🎓 Data Analyst Portfolio Highlights

This project demonstrates key skills for a **Data Analyst** role:

### 1. SQL Proficiency
- **Normalized schema design** — 6 tables with foreign key relationships
- **Window functions** — `RANK()`, cumulative sums for bus factor calculation
- **CTEs** — Cohort retention analysis with multi-step queries
- **Complex aggregations** — PR size buckets with CASE statements
- **Performance optimization** — Strategic indexes on frequently queried columns

### 2. Python & Data Engineering
- **ETL Pipeline** — Extract (GitHub API), Transform (Pandas), Load (SQLite)
- **API Integration** — Rate limit handling, pagination, error management
- **Data Transformation** — Pandas DataFrames, datetime parsing, JSON handling
- **Incremental Loading** — Upsert logic with conflict resolution

### 3. Data Analysis & Statistics
- **Cohort Analysis** — New contributor retention over time
- **Distribution Analysis** — PR merge time percentiles, issue response histograms
- **Scoring Algorithm** — Multi-dimensional compatibility scoring (0-100)
- **Business Metrics** — Merge rate, bus factor, maintainer responsiveness

### 4. Data Visualization
- **Plotly Interactive Charts** — Line, bar, histogram, pie, scatter, heatmap
- **Radar Charts** — Multi-dimensional health assessment
- **Gauge Charts** — Compatibility score visualization
- **Responsive Layouts** — Streamlit columns, tabs, and containers

### 5. Product Thinking
- **User Journey Design** — Two-feature structure with clear use cases
- **Actionable Insights** — Score breakdowns, strengths/concerns, next steps
- **Data Storytelling** — Progressive reveal from overview to deep-dive analytics

---

## 📊 Sample Analysis

### Repository Intelligence Dashboard
![Dashboard Screenshot — Replace with actual screenshot]

**Key Metrics Provided:**
- Top 15 contributors with commit counts and line changes
- PR merge rate and time-to-merge distribution
- Maintainer responsiveness score (0-100)
- Bus factor and contributor concentration
- Weekly activity trends (commits, PRs, issues)
- Good first issues for newcomers

### Compatibility Scorer
![Scorer Screenshot — Replace with actual screenshot]

**Scoring Dimensions:**
1. **Tech Alignment (0-25 pts)** — Your skills vs. repo's language
2. **Community Fit (0-25 pts)** — Activity level, review culture
3. **Entry Barrier (0-25 pts)** — Good first issues, first-time PR merge rate
4. **Time Commitment (0-25 pts)** — PR complexity vs. your availability

**Output:** Letter grade (A-F), recommendation, detailed breakdown, and next steps.

---

## 🧪 Testing & Validation

### Recommended Test Repositories

| Repository | Activity | Notes |
|------------|----------|-------|
| `sugarlabs/musicblocks` | Medium | JS-heavy, moderate community |
| `microsoft/vscode` | Very High | Large, active community |
| `facebook/react` | Very High | High volume, good baseline |
| `psf/requests` | Medium | Python, responsive maintainers |

### Running the Tests

```bash
# Analyze a test repository
streamlit run app.py

# In the sidebar, enter: sugarlabs/musicblocks
# Click "Analyze"
```

---

## 🔍 SQL Query Showcase

### Example 1: Contributor Retention Cohort (CTE + Window Functions)

```sql
WITH first_contribution AS (
    SELECT
        author_username,
        strftime('%Y-%m', MIN(committed_at)) AS cohort_month
    FROM commits
    WHERE repo_id = ?
    GROUP BY author_username
),
monthly_activity AS (
    SELECT DISTINCT
        author_username,
        strftime('%Y-%m', committed_at) AS active_month
    FROM commits
    WHERE repo_id = ?
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
ORDER BY f.cohort_month, m.active_month;
```

### Example 2: PR Size Analysis (CASE + Aggregation)

```sql
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
WHERE repo_id = ?
GROUP BY size_bucket
ORDER BY MIN(additions + deletions);
```

---

## 💡 Future Enhancements

- [ ] **Real-time sync** — Background job to keep data fresh
- [ ] **Historical tracking** — Track health metrics over time
- [ ] **Comparison mode** — Compare multiple repositories side-by-side
- [ ] **Export reports** — PDF/CSV export of analytics
- [ ] **API endpoint** — REST API for programmatic access
- [ ] **ML predictions** — Predict PR merge likelihood

---

## 📄 License

MIT License — See [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **GitHub API** — For providing rich repository data
- **Streamlit** — For the excellent dashboard framework
- **Plotly** — For interactive visualization capabilities

---

## 📬 Contact

Built by **[Your Name]**
[GitHub](https://github.com/yourusername) | [LinkedIn](https://linkedin.com/in/yourusername)

---

**OSI Dashboard v3.0** — *Making open source contribution decisions data-driven.*
