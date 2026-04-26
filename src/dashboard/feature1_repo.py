import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger

from src.analytics.contributor_analytics import (
    get_top_contributors,
    get_contributor_activity_over_time,
    get_contributor_retention,
    get_bus_factor,
)
from src.analytics.pr_analytics import (
    get_pr_merge_rate,
    get_pr_merge_time_distribution,
    get_pr_activity_over_time,
    get_pr_size_analysis,
    get_first_time_contributor_prs,
)
from src.analytics.maintainer_analytics import (
    get_maintainer_activity,
    get_issue_response_time,
    get_issue_close_rate,
)
from src.analytics.health_analytics import (
    get_community_health_summary,
    get_good_first_issues,
    get_weekly_activity_trend,
)
from src.dashboard.components import section_header, metric_card, info_callout


def render_feature1(conn: sqlite3.Connection, repo_id: int):
    """
    Render Feature 1: Repository Intelligence Dashboard.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
    """
    st.title("📊 Repository Intelligence Dashboard")

    # Get repo metadata
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
    repo_row = cursor.fetchone()

    if not repo_row:
        st.error("Repository not found in database")
        return

    repo = dict(repo_row)

    # Display repo header
    st.markdown(f"## {repo['full_name']}")
    if repo.get("description"):
        st.caption(repo["description"])

    st.markdown("---")

    # Create tabs
    tabs = st.tabs([
        "📈 Overview",
        "👥 Contributors",
        "🔀 Pull Requests",
        "🐛 Issues & Maintainers",
        "📊 Summary"
    ])

    # Tab 1: Overview
    with tabs[0]:
        render_overview_tab(conn, repo_id, repo)

    # Tab 2: Contributors
    with tabs[1]:
        render_contributors_tab(conn, repo_id)

    # Tab 3: Pull Requests
    with tabs[2]:
        render_prs_tab(conn, repo_id)

    # Tab 4: Issues & Maintainers
    with tabs[3]:
        render_issues_tab(conn, repo_id)

    # Tab 5: Summary
    with tabs[4]:
        render_summary_tab(conn, repo_id, repo)


def render_overview_tab(conn: sqlite3.Connection, repo_id: int, repo: dict):
    """Render Overview tab."""
    section_header("Repository Metrics", "Key statistics at a glance")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("⭐ Stars", f"{repo.get('stars', 0):,}")

    with col2:
        metric_card("🍴 Forks", f"{repo.get('forks', 0):,}")

    with col3:
        metric_card("🗣️ Language", repo.get("primary_language", "N/A"))

    with col4:
        metric_card("📂 Open Issues", f"{repo.get('open_issues', 0):,}")

    st.markdown("---")

    # Community Health Summary
    section_header("Community Health Metrics", "Overall project health indicators")

    health = get_community_health_summary(conn, repo_id)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric_card("PR Merge Rate", f"{health['merge_rate']:.1f}%")

    with col2:
        metric_card("Avg Merge Time", f"{health['avg_merge_time_days']:.1f} days")

    with col3:
        metric_card("Bus Factor", str(health['bus_factor']))

    with col4:
        metric_card("Good First Issues", str(health['good_first_issues_count']))

    st.markdown("---")

    # Weekly Activity Trend
    section_header("Weekly Activity Trend", "Commits, PRs, and issues over the last 12 weeks")

    activity_df = get_weekly_activity_trend(conn, repo_id, weeks=12)

    if not activity_df.empty:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=activity_df["week"],
            y=activity_df["commit_count"],
            mode="lines+markers",
            name="Commits",
            line=dict(color="#1f77b4", width=2),
        ))

        fig.add_trace(go.Scatter(
            x=activity_df["week"],
            y=activity_df["pr_count"],
            mode="lines+markers",
            name="Pull Requests",
            line=dict(color="#ff7f0e", width=2),
        ))

        fig.add_trace(go.Scatter(
            x=activity_df["week"],
            y=activity_df["issue_count"],
            mode="lines+markers",
            name="Issues",
            line=dict(color="#2ca02c", width=2),
        ))

        fig.update_layout(
            title="Weekly Activity",
            xaxis_title="Week",
            yaxis_title="Count",
            hovermode="x unified",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        info_callout("No activity data available for the selected time period", "info")


def render_contributors_tab(conn: sqlite3.Connection, repo_id: int):
    """Render Contributors tab."""
    section_header("Top Contributors", "Most active contributors in the last 90 days")

    top_contributors = get_top_contributors(conn, repo_id, top_n=15, days=90)

    if not top_contributors.empty:
        # Top Contributors Bar Chart
        fig = px.bar(
            top_contributors,
            x="commit_count",
            y="author_username",
            orientation="h",
            color="additions",
            color_continuous_scale="Viridis",
            hover_data=["deletions", "active_days", "last_active"],
            title="Top 15 Contributors by Commit Count",
        )

        fig.update_layout(
            yaxis=dict(autorange="reversed"),
            xaxis_title="Commits",
            yaxis_title="Contributor",
            height=500,
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        info_callout("No contributor data available", "info")

    st.markdown("---")

    # Bus Factor
    section_header("Bus Factor", "Project resilience indicator")

    bus_data = get_bus_factor(conn, repo_id, days=90)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Bus Factor", bus_data["bus_factor"])
        st.caption("Minimum contributors who wrote > 50% of code")

    with col2:
        st.metric("Top Contributor Share", f"{bus_data['top_contributor_share']:.1f}%")
        st.caption("Percentage of commits by top contributor")

    if bus_data["bus_factor"] <= 2:
        info_callout("⚠️ Low bus factor indicates high concentration risk", "warning")
    elif bus_data["bus_factor"] <= 5:
        info_callout("Bus factor is moderate. Project has some resilience", "info")
    else:
        info_callout("✓ Healthy bus factor. Project is well-distributed", "success")

    st.markdown("---")

    # Contributor Retention Cohort
    section_header("Contributor Retention Cohort", "How well does the project retain new contributors?")

    retention_df = get_contributor_retention(conn, repo_id)

    if not retention_df.empty and len(retention_df) > 5:
        # Pivot for heatmap
        pivot_df = retention_df.pivot_table(
            index="cohort_month",
            columns="active_month",
            values="retention_pct",
            fill_value=0
        )

        fig = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale="RdYlGn",
            text=pivot_df.values,
            texttemplate="%{text:.0f}%",
            textfont={"size": 10},
            colorbar=dict(title="Retention %"),
        ))

        fig.update_layout(
            title="Contributor Retention by Cohort",
            xaxis_title="Active Month",
            yaxis_title="Cohort Month",
            height=400,
        )

        st.plotly_chart(fig, use_container_width=True)
        st.caption("Each cell shows the % of contributors from a cohort who were active in a given month")
    else:
        info_callout("Not enough data for cohort analysis", "info")


def render_prs_tab(conn: sqlite3.Connection, repo_id: int):
    """Render Pull Requests tab."""
    section_header("PR Merge Rate", "How many PRs get merged vs rejected?")

    merge_data = get_pr_merge_rate(conn, repo_id, days=90)

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Total PRs Closed", merge_data["total"])
        st.metric("Merged", merge_data["merged"])
        st.metric("Rejected", merge_data["rejected"])
        st.metric("Merge Rate", f"{merge_data['merge_rate']:.1f}%")

    with col2:
        if merge_data["total"] > 0:
            fig = go.Figure(data=[go.Pie(
                labels=["Merged", "Rejected"],
                values=[merge_data["merged"], merge_data["rejected"]],
                hole=0.4,
                marker=dict(colors=["#2ecc71", "#e74c3c"]),
                textinfo="label+percent",
            )])

            fig.update_layout(
                title="PR Merge Rate (Last 90 Days)",
                height=300,
            )

            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Merge Time Distribution
    section_header("Merge Time Distribution", "How long does it take for PRs to get merged?")

    merge_times = get_pr_merge_time_distribution(conn, repo_id, days=90)

    if not merge_times.empty:
        median_time = merge_times["merge_time_hours"].median()
        p90_time = merge_times["merge_time_hours"].quantile(0.9)

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Median Merge Time", f"{median_time:.1f} hours")

        with col2:
            st.metric("90th Percentile", f"{p90_time:.1f} hours")

        fig = px.histogram(
            merge_times,
            x="merge_time_hours",
            nbins=30,
            title="Distribution of PR Merge Times",
            labels={"merge_time_hours": "Merge Time (hours)"},
        )

        fig.add_vline(x=median_time, line_dash="dash", line_color="red", annotation_text="Median")
        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True)
    else:
        info_callout("No merge time data available", "info")

    st.markdown("---")

    # PR Size Analysis
    section_header("PR Size vs Merge Rate", "Do smaller PRs get merged more often?")

    size_data = get_pr_size_analysis(conn, repo_id)

    if not size_data.empty:
        fig = go.Figure()

        fig.add_trace(go.Bar(
            x=size_data["size_bucket"],
            y=size_data["total_prs"],
            name="Total PRs",
            marker_color="#3498db",
        ))

        fig.add_trace(go.Scatter(
            x=size_data["size_bucket"],
            y=size_data["merge_rate_pct"],
            name="Merge Rate %",
            yaxis="y2",
            mode="lines+markers",
            marker=dict(size=10, color="#e74c3c"),
            line=dict(width=3),
        ))

        fig.update_layout(
            title="PR Size Analysis",
            xaxis_title="PR Size",
            yaxis=dict(title="Total PRs"),
            yaxis2=dict(title="Merge Rate %", overlaying="y", side="right"),
            height=400,
            hovermode="x unified",
        )

        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(size_data, use_container_width=True)
    else:
        info_callout("No PR size data available", "info")

    st.markdown("---")

    # First-Time Contributors
    section_header("First-Time Contributor Friendliness", "Are newcomers welcomed?")

    ftc_data = get_first_time_contributor_prs(conn, repo_id)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("First-Time PRs", ftc_data["first_time_pr_count"])

    with col2:
        st.metric("Merge Rate", f"{ftc_data['first_time_merge_rate']:.1f}%")

    if ftc_data["first_time_merge_rate"] >= 70:
        info_callout("✓ Very welcoming to first-time contributors!", "success")
    elif ftc_data["first_time_merge_rate"] >= 50:
        info_callout("Moderately welcoming to newcomers", "info")
    else:
        info_callout("⚠️ First-time contributors face challenges getting PRs merged", "warning")


def render_issues_tab(conn: sqlite3.Connection, repo_id: int):
    """Render Issues & Maintainers tab."""
    section_header("Issue Management", "How responsive are maintainers to issues?")

    close_data = get_issue_close_rate(conn, repo_id, days=90)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Issues", close_data["total"])

    with col2:
        st.metric("Close Rate", f"{close_data['close_rate']:.1f}%")

    with col3:
        st.metric("Avg Close Time", f"{close_data['avg_close_time_days']:.1f} days")

    # Issue response time
    response_times = get_issue_response_time(conn, repo_id, days=90)

    if not response_times.empty:
        median_response = response_times["response_time_hours"].median()

        st.metric("Median Response Time", f"{median_response:.1f} hours")

        fig = px.histogram(
            response_times,
            x="response_time_hours",
            nbins=25,
            title="Issue Response Time Distribution",
            labels={"response_time_hours": "Response Time (hours)"},
        )

        fig.add_vline(x=median_response, line_dash="dash", line_color="red", annotation_text="Median")
        fig.update_layout(height=400)

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Maintainer Activity
    section_header("Maintainer Activity", "Who is reviewing PRs?")

    maintainers = get_maintainer_activity(conn, repo_id, days=90)

    if not maintainers.empty:
        st.dataframe(maintainers, use_container_width=True)
    else:
        info_callout("No maintainer review data available", "info")

    st.markdown("---")

    # Good First Issues
    section_header("Good First Issues", "Entry points for new contributors")

    good_issues = get_good_first_issues(conn, repo_id, limit=20)

    if not good_issues.empty:
        st.dataframe(good_issues, use_container_width=True)
    else:
        info_callout("No good first issues found", "info")


def render_summary_tab(conn: sqlite3.Connection, repo_id: int, repo: dict):
    """Render Summary tab with radar chart and final verdict."""
    section_header("Repository Health Radar", "Multi-dimensional health assessment")

    health = get_community_health_summary(conn, repo_id)
    bus_data = get_bus_factor(conn, repo_id)

    # Calculate radar chart scores (0-100 scale)
    activity_score = min(health["commit_frequency_per_week"] / 50 * 100, 100)
    community_score = (health["merge_rate"] + health["pr_comment_avg"] * 10) / 2
    maintainer_score = health["maintainer_responsiveness"]
    beginner_score = min(health["good_first_issues_count"] / 10 * 100, 100)
    momentum_score = min((100 - health["avg_merge_time_days"] * 2), 100) if health["avg_merge_time_days"] > 0 else 50

    categories = ["Activity", "Community", "Maintainers", "Beginner-Friendly", "Momentum"]
    values = [activity_score, community_score, maintainer_score, beginner_score, momentum_score]

    fig = go.Figure()

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill="toself",
        line=dict(color="#3498db", width=2),
        marker=dict(size=8),
        name=repo["full_name"],
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100]),
        ),
        showlegend=False,
        title="Repository Health Score",
        height=500,
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Final Verdict
    section_header("Final Verdict", "Should you contribute here?")

    overall_score = sum(values) / len(values)

    if overall_score >= 70:
        st.success(f"✓ **Excellent Repository** (Score: {overall_score:.1f}/100)")
        st.markdown("""
        This repository shows strong signs of health across all dimensions:
        - Active community with regular contributions
        - Responsive maintainers
        - Welcoming to newcomers
        - Good momentum and project velocity

        **Recommendation:** This is a great place to contribute!
        """)
    elif overall_score >= 50:
        st.info(f"**Good Repository** (Score: {overall_score:.1f}/100)")
        st.markdown("""
        This repository shows moderate health. Some areas are strong while others could improve.

        **Recommendation:** Review the tab details to understand strengths and weaknesses before contributing.
        """)
    else:
        st.warning(f"⚠️ **Challenging Repository** (Score: {overall_score:.1f}/100)")
        st.markdown("""
        This repository shows signs of challenges in community health, maintainer responsiveness, or activity levels.

        **Recommendation:** Proceed with caution. Consider using the Compatibility Scorer to get a personalized assessment.
        """)
