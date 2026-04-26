import streamlit as st
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from src.analytics.compatibility_scorer import calculate_compatibility_score
from src.dashboard.components import section_header, info_callout


def render_feature2(conn: sqlite3.Connection, repo_id: int):
    """
    Render Feature 2: Contributor Compatibility Scorer.

    Args:
        conn: SQLite connection
        repo_id: Repository ID
    """
    st.title("🎯 Contributor Compatibility Scorer")

    # Get repo metadata
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
    repo_row = cursor.fetchone()

    if not repo_row:
        st.error("Repository not found in database")
        return

    repo = dict(repo_row)

    st.markdown(f"### Analyzing fit for: **{repo['full_name']}**")
    st.caption("Fill out your profile below to get a personalized compatibility score")

    st.markdown("---")

    # User Profile Form
    section_header("👤 Your Contributor Profile", "Tell us about your skills and preferences")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)

        with col1:
            tech_stack = st.multiselect(
                "Tech Stack",
                options=[
                    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go",
                    "Rust", "PHP", "Ruby", "Swift", "Kotlin", "HTML/CSS", "SQL",
                    "React", "Vue", "Angular", "Node.js", "Django", "Flask", "Spring",
                ],
                help="Select the languages and frameworks you're comfortable with"
            )

            experience_level = st.select_slider(
                "Experience Level",
                options=["beginner", "intermediate", "advanced"],
                value="intermediate"
            )

            contribution_type = st.multiselect(
                "Contribution Types You Prefer",
                options=["code", "docs", "testing", "design", "issues"],
                default=["code"]
            )

        with col2:
            weekly_hours = st.slider(
                "Weekly Hours Available",
                min_value=1,
                max_value=40,
                value=5,
                help="How many hours per week can you dedicate?"
            )

            interests = st.multiselect(
                "Your Interests",
                options=[
                    "backend", "frontend", "fullstack", "ml", "ai", "devtools",
                    "data", "mobile", "web", "cli", "api", "database", "security"
                ],
                help="What areas are you most interested in?"
            )

        st.markdown("### Preferences")

        col1, col2, col3 = st.columns(3)

        with col1:
            has_oss_exp = st.checkbox(
                "I have open source experience",
                value=False
            )

        with col2:
            comfortable_reviews = st.checkbox(
                "I'm comfortable with code reviews",
                value=True
            )

        with col3:
            prefers_active = st.checkbox(
                "I prefer active communities",
                value=True
            )

        submitted = st.form_submit_button("🎯 Calculate My Compatibility Score", use_container_width=True)

    # Calculate and display score if form submitted
    if submitted:
        if not tech_stack:
            st.error("Please select at least one technology from your tech stack")
            return

        # Build user profile dict
        user_profile = {
            "tech_stack": tech_stack,
            "experience_level": experience_level,
            "contribution_type": contribution_type,
            "weekly_hours_available": weekly_hours,
            "interests": interests,
            "has_open_source_exp": has_oss_exp,
            "comfortable_with_reviews": comfortable_reviews,
            "prefers_active_community": prefers_active,
        }

        # Calculate compatibility
        with st.spinner("Calculating your compatibility score..."):
            result = calculate_compatibility_score(user_profile, conn, repo_id)

        st.success("✓ Compatibility analysis complete!")

        st.markdown("---")

        # Display Score Dashboard
        render_score_dashboard(result, repo, user_profile)


def render_score_dashboard(result: dict, repo: dict, user_profile: dict):
    """
    Render the compatibility score dashboard.

    Args:
        result: Compatibility score result dict
        repo: Repository metadata dict
        user_profile: User profile dict
    """
    section_header("Your Compatibility Score", f"How well you match {repo['full_name']}")

    # Large score gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=result["total_score"],
        domain={"x": [0, 1], "y": [0, 1]},
        title={"text": "Compatibility Score", "font": {"size": 24}},
        delta={"reference": 50},
        gauge={
            "axis": {"range": [None, 100]},
            "bar": {"color": _get_gauge_color(result["total_score"])},
            "steps": [
                {"range": [0, 35], "color": "#e74c3c"},
                {"range": [35, 50], "color": "#f39c12"},
                {"range": [50, 65], "color": "#f1c40f"},
                {"range": [65, 80], "color": "#2ecc71"},
                {"range": [80, 100], "color": "#27ae60"},
            ],
            "threshold": {
                "line": {"color": "black", "width": 4},
                "thickness": 0.75,
                "value": result["total_score"],
            },
        },
    ))

    fig.update_layout(height=350)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.plotly_chart(fig, use_container_width=True)

    # Grade and Recommendation
    col1, col2 = st.columns(2)

    with col1:
        grade_color = _get_grade_color(result["grade"])
        st.markdown(f"<h1 style='text-align: center; color: {grade_color};'>{result['grade']}</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>Grade</p>", unsafe_allow_html=True)

    with col2:
        st.markdown(f"**Recommendation:**")
        st.info(result["recommendation"])

    st.markdown("---")

    # Score Breakdown
    section_header("Score Breakdown", "How each dimension contributed to your score")

    breakdown = result["breakdown"]

    # Horizontal bar chart
    dimensions = ["Tech Alignment", "Community Fit", "Entry Barrier", "Time Commitment"]
    scores = [
        breakdown["tech_alignment"]["score"],
        breakdown["community_fit"]["score"],
        breakdown["entry_barrier"]["score"],
        breakdown["time_commitment"]["score"],
    ]
    max_scores = [25, 25, 25, 25]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=dimensions,
        x=scores,
        orientation="h",
        marker=dict(color=_get_bar_colors(scores, max_scores)),
        text=[f"{s}/{m}" for s, m in zip(scores, max_scores)],
        textposition="inside",
        name="Your Score",
    ))

    fig.add_trace(go.Bar(
        y=dimensions,
        x=[m - s for s, m in zip(scores, max_scores)],
        orientation="h",
        marker=dict(color="lightgray"),
        showlegend=False,
    ))

    fig.update_layout(
        barmode="stack",
        title="Dimension Scores",
        xaxis=dict(title="Score", range=[0, 25]),
        yaxis=dict(autorange="reversed"),
        height=300,
    )

    st.plotly_chart(fig, use_container_width=True)

    # Dimension Details
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**🎯 Tech Alignment**")
        st.caption(f"{breakdown['tech_alignment']['label']}: {breakdown['tech_alignment']['detail']}")

        st.markdown("**👥 Community Fit**")
        st.caption(f"{breakdown['community_fit']['label']}: {breakdown['community_fit']['detail']}")

    with col2:
        st.markdown("**🚪 Entry Barrier**")
        st.caption(f"{breakdown['entry_barrier']['label']}: {breakdown['entry_barrier']['detail']}")

        st.markdown("**⏰ Time Commitment**")
        st.caption(f"{breakdown['time_commitment']['label']}: {breakdown['time_commitment']['detail']}")

    st.markdown("---")

    # Strengths
    if result["strengths"]:
        section_header("✓ Strengths", "What works in your favor")
        for strength in result["strengths"]:
            st.markdown(f"- {strength}")

    st.markdown("---")

    # Concerns
    if result["concerns"]:
        section_header("⚠ Concerns", "Potential challenges to consider")
        for concern in result["concerns"]:
            st.markdown(f"- {concern}")

    st.markdown("---")

    # Action Items
    section_header("→ Next Steps", "Recommended actions based on your score")
    for action in result["action_items"]:
        st.markdown(f"- {action}")

    st.markdown("---")

    # Comparison Table
    section_header("Profile vs Repository Reality", "How your profile aligns with this repo")

    comparison_data = _build_comparison_table(user_profile, breakdown, repo)

    st.table(comparison_data)


def _get_gauge_color(score: int) -> str:
    """Get gauge color based on score."""
    if score >= 80:
        return "#27ae60"
    elif score >= 65:
        return "#2ecc71"
    elif score >= 50:
        return "#f1c40f"
    elif score >= 35:
        return "#f39c12"
    else:
        return "#e74c3c"


def _get_grade_color(grade: str) -> str:
    """Get color for grade badge."""
    colors = {
        "A": "#27ae60",
        "B": "#2ecc71",
        "C": "#f1c40f",
        "D": "#f39c12",
        "F": "#e74c3c",
    }
    return colors.get(grade, "#95a5a6")


def _get_bar_colors(scores, max_scores):
    """Get colors for bar chart based on percentage."""
    colors = []
    for score, max_score in zip(scores, max_scores):
        pct = (score / max_score * 100) if max_score > 0 else 0
        if pct >= 80:
            colors.append("#27ae60")
        elif pct >= 60:
            colors.append("#2ecc71")
        elif pct >= 40:
            colors.append("#f1c40f")
        else:
            colors.append("#e74c3c")
    return colors


def _build_comparison_table(user_profile: dict, breakdown: dict, repo: dict):
    """Build comparison table data."""
    return {
        "Dimension": [
            "Tech Stack",
            "Experience Level",
            "Weekly Availability",
            "Contribution Type",
        ],
        "Your Profile": [
            ", ".join(user_profile["tech_stack"][:3]),
            user_profile["experience_level"].title(),
            f"{user_profile['weekly_hours_available']} hours/week",
            ", ".join(user_profile["contribution_type"]),
        ],
        "Repo Reality": [
            repo.get("primary_language", "N/A"),
            breakdown["community_fit"]["label"],
            breakdown["time_commitment"]["label"],
            "Code contributions",
        ],
        "Match": [
            _get_match_emoji(breakdown["tech_alignment"]["score"], 25),
            _get_match_emoji(breakdown["community_fit"]["score"], 25),
            _get_match_emoji(breakdown["time_commitment"]["score"], 25),
            "✓",
        ],
    }


def _get_match_emoji(score: int, max_score: int) -> str:
    """Get match emoji based on score percentage."""
    pct = (score / max_score * 100) if max_score > 0 else 0
    if pct >= 80:
        return "✓✓✓"
    elif pct >= 60:
        return "✓✓"
    elif pct >= 40:
        return "✓"
    else:
        return "✗"
