# OSI Dashboard — Project Proposal
> **Open Source Intelligence Platform for Data-Driven Contribution Decisions**

**Author:** Om Suneri
**Date:** March 2026
**Project Type:** Data Analyst Portfolio Project
**Status:** Implementation Complete — Ready for Review

---

## 📋 Executive Summary

The **OSI Dashboard** is a comprehensive analytics platform that solves a critical problem in open-source contribution: **lack of data-driven insights** when choosing repositories to contribute to. Developers currently rely on intuition and basic GitHub metrics (stars, forks) which don't reveal community health, maintainer responsiveness, or personal compatibility.

This project demonstrates **end-to-end data analyst skills** — from ETL pipeline design to SQL analytics to interactive visualizations — while solving a real-world problem for the open-source community.

---

## 🎯 Problem Statement

### Current Challenges

1. **Information Overload**
   - GitHub has 100M+ repositories
   - No unified view of repository health metrics
   - Difficult to assess maintainer responsiveness

2. **Wasted Effort**
   - Contributors invest time in PRs that never get reviewed
   - ~30% of first-time PRs are ignored or rejected
   - No way to predict contribution success before starting

3. **Hidden Risk Factors**
   - Bus factor (project concentration risk) is invisible
   - Toxic communities aren't discoverable until you engage
   - Time commitment mismatches waste developer hours

### Target Users

- **Open-source contributors** seeking the right project to contribute to
- **Data analysts** demonstrating SQL, Python, and visualization skills
- **Engineering managers** evaluating community health for dependency decisions

---

## 💡 Solution Overview

The OSI Dashboard provides **two interconnected features**:

### Feature 1: Repository Intelligence Dashboard
**Problem Solved:** "I found a repo — should I contribute here?"

**Solution:** Comprehensive analytics revealing:
- Contributor activity patterns and retention rates
- PR merge probability and time-to-merge distribution
- Maintainer responsiveness scoring (0-100)
- Community health radar chart (5 dimensions)
- Bus factor risk assessment

### Feature 2: Contributor Compatibility Scorer
**Problem Solved:** "Am I a good fit for this repository?"

**Solution:** Personalized 0-100 compatibility score based on:
- Tech stack alignment (your skills vs. repo's language)
- Community culture fit (activity level, review intensity)
- Entry barrier analysis (beginner-friendliness)
- Time commitment match (PR complexity vs. your availability)

**Output:** Letter grade (A-F), detailed breakdown, actionable next steps.

---

## 🏗️ System Architecture

### High-Level Data Flow

```
┌─────────────────┐
│  GitHub API     │ ← REST (rate-limit aware)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ETL Pipeline   │ ← Python + Pandas
│  - Extract      │
│  - Transform    │
│  - Load         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │ ← 6 normalized tables
│  - Repos        │   Advanced SQL (CTEs, Window Functions)
│  - Commits      │
│  - PRs/Issues   │
│  - Reviews      │
│  - Contributors │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Analytics      │ ← SQL + Pandas
│  - 5 modules    │   Statistical analysis
│  - Scoring      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Streamlit UI   │ ← Interactive dashboard
│  - 12+ charts   │   Plotly visualizations
│  - 2 features   │
└─────────────────┘
```

### Database Schema Design

**6 Normalized Tables:**

```sql
repositories (1) ──┐
                   │
commits (N) ───────┼──> repo_id
contributors (N) ──┤
pull_requests (N) ─┤
issues (N) ────────┤
                   │
reviews (N) ───────┴──> pr_id + repo_id
```

**Key Design Decisions:**
- **Normalized structure** prevents data duplication
- **Strategic indexes** on frequently queried columns (repo_id, dates, usernames)
- **JSON storage** for variable-length arrays (labels)
- **Temporal fields** enable time-series and cohort analysis

---

## 🔧 Technology Stack & Rationale

### Data Layer

| Technology | Purpose | Why This Choice |
|------------|---------|-----------------|
| **SQLite** | Data storage | Portable, zero-config, perfect for portfolio projects |
| **SQLAlchemy** | ORM (models only) | Schema management, but raw SQL for analytics |
| **Raw SQL** | Analytics queries | Demonstrates SQL proficiency (CTEs, window functions) |

### Processing Layer

| Technology | Purpose | Why This Choice |
|------------|---------|-----------------|
| **Python 3.11+** | Core language | Industry standard for data engineering |
| **Pandas** | Data transformation | DataFrame manipulation, time-series analysis |
| **Requests** | API client | GitHub REST API integration with retry logic |
| **Loguru** | Logging | Structured logging for debugging |

### Visualization Layer

| Technology | Purpose | Why This Choice |
|------------|---------|-----------------|
| **Streamlit** | Dashboard framework | Rapid prototyping, data-focused UI |
| **Plotly** | Interactive charts | 12+ chart types, professional visualizations |

### Data Source

| API | Endpoints Used | Rate Limits |
|-----|----------------|-------------|
| **GitHub REST** | repos, commits, pulls, issues, reviews, contributors | 5,000 req/hr (authenticated) |

---

## 📊 Key Features & Technical Implementation

### 1. Contributor Analytics

**Business Value:** Identify project concentration risk and contributor retention

**Technical Implementation:**

**SQL Showcase — Cohort Retention Analysis (CTE + Window Functions):**
```sql
WITH first_contribution AS (
    SELECT
        author_username,
        strftime('%Y-%m', MIN(committed_at)) AS cohort_month
    FROM commits WHERE repo_id = ?
    GROUP BY author_username
),
monthly_activity AS (
    SELECT DISTINCT
        author_username,
        strftime('%Y-%m', committed_at) AS active_month
    FROM commits WHERE repo_id = ?
)
SELECT
    f.cohort_month,
    COUNT(DISTINCT f.author_username) AS cohort_size,
    m.active_month,
    COUNT(DISTINCT m.author_username) AS retained,
    ROUND(100.0 * COUNT(DISTINCT m.author_username) /
          COUNT(DISTINCT f.author_username), 1) AS retention_pct
FROM first_contribution f
JOIN monthly_activity m ON f.author_username = m.author_username
GROUP BY f.cohort_month, m.active_month
ORDER BY f.cohort_month, m.active_month;
```

**Pandas Analysis — Bus Factor Calculation:**
```python
# Get contributor commit shares
contributor_commits = pd.read_sql_query(sql, conn)
contributor_commits['commit_share'] = (
    contributor_commits['commits'] / contributor_commits['commits'].sum()
)

# Calculate bus factor: minimum contributors for >50% commits
cumulative_share = contributor_commits.sort_values('commits', ascending=False)
cumulative_share['cumsum'] = cumulative_share['commit_share'].cumsum()
bus_factor = (cumulative_share['cumsum'] <= 0.5).sum()
```

**Visualizations:**
- Top 15 contributors bar chart (color by additions/deletions)
- Contributor retention heatmap (cohort × month)
- Bus factor metric with risk indicator

---

### 2. Pull Request Analytics

**Business Value:** Predict PR success probability and time-to-merge

**Technical Implementation:**

**SQL Showcase — PR Size Buckets with CASE:**
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

**Pandas Analysis — Time Distribution:**
```python
# Calculate merge time percentiles
merge_times['hours'] = (
    pd.to_datetime(merge_times['merged_at']) -
    pd.to_datetime(merge_times['created_at'])
).dt.total_seconds() / 3600

percentiles = {
    'median': merge_times['hours'].median(),
    'p90': merge_times['hours'].quantile(0.9),
    'p95': merge_times['hours'].quantile(0.95)
}
```

**Visualizations:**
- Merge rate donut chart (merged vs. rejected)
- Time-to-merge histogram with median/p90 annotations
- PR size vs. merge rate scatter plot
- Weekly PR activity grouped bar chart

---

### 3. Maintainer Responsiveness Scoring

**Business Value:** Assess whether your contribution will be reviewed promptly

**Technical Implementation:**

**Composite Score Algorithm (0-100 points):**

```python
def calculate_responsiveness_score(conn, repo_id, days=90):
    # 1. Issue response time (0-40 pts)
    response_times = get_issue_response_times(conn, repo_id, days)
    avg_response_hours = response_times['hours'].mean()

    if avg_response_hours <= 24:
        response_score = 40
    elif avg_response_hours <= 168:  # 1 week
        response_score = 30
    elif avg_response_hours <= 720:  # 1 month
        response_score = 20
    else:
        response_score = 10

    # 2. PR review coverage (0-30 pts)
    review_coverage = get_pr_review_coverage(conn, repo_id, days)
    coverage_pct = review_coverage['prs_with_reviews'] / review_coverage['total_prs']
    coverage_score = min(coverage_pct * 30, 30)

    # 3. Time to first review (0-30 pts)
    first_review_times = get_time_to_first_review(conn, repo_id, days)
    avg_first_review_hours = first_review_times['hours'].mean()

    if avg_first_review_hours <= 48:
        first_review_score = 30
    elif avg_first_review_hours <= 168:
        first_review_score = 20
    else:
        first_review_score = 10

    return response_score + coverage_score + first_review_score
```

**SQL Queries:**
- Issue response time distribution
- PR review coverage percentage
- Maintainer activity table (reviews by user)

**Visualizations:**
- Issue response time histogram
- Maintainer activity table (sortable)
- Responsiveness score gauge (0-100)

---

### 4. Community Health Radar

**Business Value:** Multi-dimensional health assessment at a glance

**Technical Implementation:**

**5 Health Dimensions:**

```python
def calculate_health_scores(conn, repo_id):
    return {
        'activity': min(commit_frequency / 50 * 100, 100),
        'community': (merge_rate + pr_comment_avg * 10) / 2,
        'maintainers': responsiveness_score,  # from previous section
        'beginner_friendly': min(good_first_issues / 10 * 100, 100),
        'momentum': min((100 - avg_merge_days * 2), 100)
    }
```

**Visualization:**
- Plotly Scatterpolar radar chart (5 axes)
- Color-coded by score range
- Filled area shows overall health

---

### 5. Compatibility Scorer

**Business Value:** Personalized recommendation before investing time

**Technical Implementation:**

**4-Dimensional Scoring Algorithm:**

```python
# Dimension 1: Tech Alignment (0-25 pts)
def score_tech_alignment(user_profile, repo_meta):
    user_stack = user_profile['tech_stack']
    repo_language = repo_meta['primary_language']

    score = 0
    if repo_language in user_stack:
        score += 15  # Primary language match

    score += min(len(user_stack), 2) * 5  # Diversity bonus
    return min(score, 25)

# Dimension 2: Community Fit (0-25 pts)
def score_community_fit(user_profile, health_metrics):
    score = 0

    # Active community preference
    if user_profile['prefers_active']:
        if health_metrics['commit_frequency'] > 50:
            score += 10

    # Review culture comfort
    if user_profile['comfortable_with_reviews']:
        if health_metrics['pr_comment_avg'] > 3:
            score += 8

    # Experience level match
    if matches_experience_level(user_profile, health_metrics):
        score += 7

    return min(score, 25)

# Dimension 3: Entry Barrier (0-25 pts)
def score_entry_barrier(good_first_issues, first_time_merge_rate):
    score = 0

    if good_first_issues >= 10:
        score += 10

    if first_time_merge_rate >= 70:
        score += 10

    score += 5  # Small PR merge time bonus

    return min(score, 25)

# Dimension 4: Time Commitment (0-25 pts)
def score_time_commitment(user_hours, pr_complexity):
    if user_hours <= 5 and pr_complexity == 'low':
        return 25
    elif user_hours > 15:
        return 25
    else:
        return 15  # Moderate match
```

**Output Format:**
```python
{
    'total_score': 78,
    'grade': 'B',
    'recommendation': 'Good fit. A few things to consider.',
    'breakdown': {
        'tech_alignment': {'score': 20, 'max': 25, 'label': 'Strong Match'},
        'community_fit': {'score': 18, 'max': 25, 'label': 'Good Fit'},
        'entry_barrier': {'score': 22, 'max': 25, 'label': 'Low Barrier'},
        'time_commitment': {'score': 18, 'max': 25, 'label': 'Good Match'}
    },
    'strengths': ['✓ Tech stack aligns well', '✓ Low entry barrier'],
    'concerns': ['⚠ Review culture is intense'],
    'action_items': ['→ Read CONTRIBUTING.md', '→ Browse open issues']
}
```

**Visualizations:**
- Gauge chart (0-100 score)
- Horizontal bar chart (dimension breakdown)
- Comparison table (your profile vs. repo reality)

---

## 🔄 ETL Pipeline Deep Dive

### Extract Phase

**GitHub API Client** (`src/etl/github_client.py`)

**Key Features:**
- Rate limit awareness (checks `X-RateLimit-Remaining` header)
- Automatic pagination for large result sets
- Exponential backoff retry logic
- Token authentication support

**Data Extracted:**
```python
{
    'meta': repo_metadata,           # 1 object
    'commits': commit_list,          # up to 500 commits
    'pull_requests': pr_list,        # all PRs with reviews
    'issues': issue_list,            # true issues only (no PRs)
    'contributors': contributor_list # all contributors
}
```

**API Calls Per Repository:**
- 1 request: Repository metadata
- 5-10 requests: Commits (paginated)
- 3-5 requests: Pull requests (paginated)
- 1-50 requests: PR reviews (per PR, limited to first 50 PRs)
- 3-5 requests: Issues (paginated)
- 1-100 requests: Issue comments (per issue, limited to first 100)
- 1 request: Contributors

**Total:** ~20-180 API requests per repository

---

### Transform Phase

**Pandas DataFrames** (`src/etl/transform.py`)

**Key Transformations:**

1. **Date Parsing:**
   ```python
   # GitHub API returns ISO 8601 strings
   # Store as-is for SQLite compatibility
   df['committed_at'] = raw['commit']['author']['date']
   ```

2. **Null Handling:**
   ```python
   # Handle deleted users, missing fields
   df['author'] = commit.get('author', {}).get('login', 'unknown')
   ```

3. **JSON Serialization:**
   ```python
   # Convert label arrays to JSON strings
   df['labels'] = df['labels'].apply(json.dumps)
   ```

4. **Type Coercion:**
   ```python
   # Boolean to integer for SQLite
   df['is_merged'] = df['merged_at'].notna().astype(int)
   ```

**Output:** 5 clean DataFrames ready for database insertion

---

### Load Phase

**Upsert Logic** (`src/etl/load.py`)

**Strategy:** INSERT ... ON CONFLICT DO UPDATE

```python
def upsert_dataframe(df, table, conflict_column):
    columns = df.columns.tolist()
    placeholders = ", ".join(["?" for _ in columns])

    # Build UPDATE clause
    update_set = ", ".join([
        f"{col} = excluded.{col}"
        for col in columns if col != conflict_column
    ])

    sql = f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({placeholders})
        ON CONFLICT({conflict_column})
        DO UPDATE SET {update_set}
    """

    cursor.executemany(sql, df.values.tolist())
```

**Load Order (Critical for Foreign Keys):**
1. Repositories → get `repo_id`
2. Commits (needed for contributor dates)
3. Contributors
4. Pull Requests → get `pr_ids`
5. Reviews (depends on `pr_ids`)
6. Issues
7. Update contributor commit dates (via SQL UPDATE)

**Error Handling:**
- Transaction rollback on any failure
- Detailed logging with traceback
- Defensive checks for None values

---

## 📈 Analytics Methodology

### Statistical Methods Used

1. **Cohort Analysis**
   - Group contributors by first contribution month
   - Track retention month-over-month
   - Output: Retention heatmap

2. **Percentile Analysis**
   - Calculate p50, p90, p95 for time-based metrics
   - Identify outliers in merge times and response times

3. **Distribution Analysis**
   - Histogram binning for merge time, PR size
   - Identify patterns (e.g., bimodal distributions)

4. **Aggregation & Grouping**
   - Weekly/monthly time-series aggregations
   - Category-based aggregations (PR size buckets)

5. **Scoring Algorithms**
   - Weighted composite scores (responsiveness, compatibility)
   - Normalization to 0-100 scale

---

## 🎨 Visualization Strategy

### Chart Type Selection

| Metric Type | Chart Used | Rationale |
|-------------|------------|-----------|
| Part-to-whole | Donut chart | Show merge rate, close rate |
| Distribution | Histogram | Time-to-merge, response time |
| Ranking | Horizontal bar | Top contributors |
| Time-series | Line chart | Weekly activity trends |
| Comparison | Grouped bar | PRs opened vs. merged |
| Correlation | Scatter plot | PR size vs. merge rate |
| Multi-dimensional | Radar chart | Health scores |
| KPI | Gauge chart | Compatibility score |
| Pattern | Heatmap | Cohort retention |

### Plotly Configuration

**Interactive Features:**
- Hover tooltips with detailed data
- Zoom/pan for time-series
- Click legends to toggle series
- Responsive width (`use_container_width=True`)

**Accessibility:**
- Color-blind friendly palettes
- High contrast text
- Clear axis labels

---

## 🎯 Expected Outcomes & Success Metrics

### For Contributors

**Before OSI Dashboard:**
- Spend 2-3 weeks on a PR that never gets reviewed
- 30% chance of first PR rejection
- No data to inform repository choice

**After OSI Dashboard:**
- ✅ 10-minute analysis reveals project health
- ✅ Compatibility score predicts success likelihood
- ✅ Data-driven decision reduces wasted effort

### For Data Analyst Portfolio

**Skills Demonstrated:**

| Category | Skills Shown | Evidence |
|----------|--------------|----------|
| **SQL** | CTEs, window functions, aggregations, joins | `contributor_retention.sql`, `pr_size_analysis.sql` |
| **Python** | ETL pipeline, API integration, error handling | `github_client.py`, `extract.py`, `transform.py` |
| **Pandas** | DataFrame manipulation, time-series, statistics | All `analytics/*.py` modules |
| **Visualization** | 12+ chart types, interactive dashboards | Plotly charts in `feature1_repo.py`, `feature2_compat.py` |
| **Data Engineering** | Schema design, indexing, incremental loading | `schema.sql`, `load.py` |
| **Product Thinking** | User journey, scoring algorithm, actionable insights | Compatibility scorer design |

---

## 📚 Technical Documentation

### Repository Structure

```
osi-dashboard/
├── app.py                        # Streamlit entry point
├── requirements.txt              # Dependencies
├── .env                          # API keys (not committed)
│
├── data/
│   └── osi_dashboard.db          # SQLite database
│
├── src/
│   ├── config.py                 # Configuration
│   │
│   ├── database/
│   │   ├── schema.sql            # CREATE TABLE statements
│   │   ├── init_db.py            # Database initialization
│   │   └── connection.py         # Connection manager
│   │
│   ├── etl/
│   │   ├── github_client.py      # GitHub API wrapper
│   │   ├── extract.py            # Data extraction
│   │   ├── transform.py          # Pandas transformations
│   │   └── load.py               # Database loading
│   │
│   ├── analytics/
│   │   ├── contributor_analytics.py
│   │   ├── pr_analytics.py
│   │   ├── maintainer_analytics.py
│   │   ├── health_analytics.py
│   │   └── compatibility_scorer.py
│   │
│   └── dashboard/
│       ├── components.py         # Reusable UI components
│       ├── feature1_repo.py      # Repository Intelligence
│       └── feature2_compat.py    # Compatibility Scorer
│
└── scripts/
    ├── seed.py                   # Load sample data
    └── reset_db.py               # Reset database
```

### Running the Project

```bash
# Install dependencies
pip install -r requirements.txt

# Configure GitHub token (optional, for higher rate limits)
echo "GITHUB_TOKEN=ghp_your_token_here" > .env

# Initialize database (automatic on first run)
python src/database/init_db.py

# Start dashboard
streamlit run app.py

# Seed sample data (optional)
python scripts/seed.py sugarlabs/musicblocks
```

### Testing Repositories

| Repository | Activity | Why Good for Testing |
|------------|----------|---------------------|
| `sugarlabs/musicblocks` | Medium | Balanced metrics, diverse contributors |
| `microsoft/vscode` | Very High | Large scale, high volume |
| `psf/requests` | Medium | Python, responsive maintainers |
| `facebook/react` | Very High | Benchmark for active projects |

---

## ✅ Conclusion

The **OSI Dashboard** successfully demonstrates end-to-end data analyst capabilities while solving a real problem for open-source contributors. The project showcases:

✅ **SQL Proficiency** — CTEs, window functions, cohort analysis
✅ **Python Engineering** — ETL pipeline, API integration, error handling
✅ **Data Analysis** — Statistical methods, scoring algorithms
✅ **Visualization** — 12+ interactive charts
✅ **Product Thinking** — User journey, actionable insights

**Ready for:** Portfolio review, technical interviews, mentor feedback

**Seeking:** Code review, architecture feedback, feature prioritization guidance

---
*Last Updated: March 29, 2026*
