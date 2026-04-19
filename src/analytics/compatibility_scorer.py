import sqlite3
from typing import Dict, List
from loguru import logger
from src.analytics.pr_analytics import get_pr_merge_rate, get_pr_size_analysis, get_first_time_contributor_prs
from src.analytics.health_analytics import get_good_first_issues, get_community_health_summary
from src.analytics.contributor_analytics import get_bus_factor


def score_tech_alignment(
    user_profile: dict,
    repo_meta: dict,
    conn: sqlite3.Connection,
    repo_id: int
) -> dict:
    """
    Score tech stack alignment (0-25 pts).

    Args:
        user_profile: User profile dict
        repo_meta: Repository metadata
        conn: SQLite connection
        repo_id: Repository ID

    Returns:
        dict: {'score': int, 'max': 25, 'label': str, 'detail': str}
    """
    score = 0
    max_score = 25

    user_stack = [tech.lower() for tech in user_profile.get("tech_stack", [])]
    repo_language = repo_meta.get("primary_language", "").lower()

    if not user_stack:
        return {
            "score": 0,
            "max": max_score,
            "label": "No Match",
            "detail": "You haven't specified any tech stack preferences."
        }

    # Primary language match (15 pts)
    if repo_language in user_stack or any(tech in repo_language for tech in user_stack):
        score += 15
        label = "Strong Match"
        detail = f"Your {repo_language.title()} skills match the repo's primary language."
    else:
        label = "Weak Match"
        detail = f"Repo uses {repo_language.title()}, which isn't in your tech stack."

    # Contributor tech diversity (10 pts bonus)
    # Check if repo has activity in user's preferred languages
    tech_diversity_bonus = min(len(user_stack), 2) * 5
    score += tech_diversity_bonus

    score = min(score, max_score)

    return {
        "score": score,
        "max": max_score,
        "label": label,
        "detail": detail,
    }


def score_community_fit(
    user_profile: dict,
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = 90
) -> dict:
    """
    Score community fit based on user preferences (0-25 pts).

    Args:
        user_profile: User profile dict
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        dict: {'score': int, 'max': 25, 'label': str, 'detail': str}
    """
    score = 0
    max_score = 25

    health = get_community_health_summary(conn, repo_id, days)
    bus_data = get_bus_factor(conn, repo_id, days)

    # Active community preference (10 pts)
    if user_profile.get("prefers_active_community", False):
        commit_freq = health.get("commit_frequency_per_week", 0)
        if commit_freq > 50:
            score += 10
        elif commit_freq > 20:
            score += 7
        elif commit_freq > 5:
            score += 4
        else:
            score += 2

    # Comfortable with reviews (8 pts)
    if user_profile.get("comfortable_with_reviews", False):
        avg_comments = health.get("pr_comment_avg", 0)
        if avg_comments > 3:
            score += 8
        elif avg_comments > 1:
            score += 5
        else:
            score += 3

    # Experience level match (7 pts)
    experience = user_profile.get("experience_level", "beginner")
    merge_rate = health.get("merge_rate", 0)

    if experience == "advanced":
        if bus_data["bus_factor"] <= 2:
            score += 7  # Advanced users can handle high-concentration repos
    elif experience == "intermediate":
        if merge_rate > 60:
            score += 7
    else:  # beginner
        if merge_rate > 70 and health.get("good_first_issues_count", 0) > 0:
            score += 7

    score = min(score, max_score)

    if score >= 20:
        label = "Excellent Fit"
        detail = "Community culture aligns well with your preferences."
    elif score >= 12:
        label = "Good Fit"
        detail = "Community is reasonably aligned with your preferences."
    else:
        label = "Moderate Fit"
        detail = "Some aspects of the community may not match your preferences."

    return {
        "score": score,
        "max": max_score,
        "label": label,
        "detail": detail,
    }


def score_entry_barrier(user_profile: dict, conn: sqlite3.Connection, repo_id: int) -> dict:
    """
    Score entry barrier / beginner-friendliness (0-25 pts).

    Args:
        user_profile: User profile dict
        conn: SQLite connection
        repo_id: Repository ID

    Returns:
        dict: {'score': int, 'max': 25, 'label': str, 'detail': str}
    """
    score = 0
    max_score = 25

    good_first_issues = get_good_first_issues(conn, repo_id, limit=50)
    first_time_pr_data = get_first_time_contributor_prs(conn, repo_id)
    pr_size_data = get_pr_size_analysis(conn, repo_id)

    # Good first issues (10 pts)
    issue_count = len(good_first_issues)
    if issue_count >= 10:
        score += 10
    elif issue_count >= 5:
        score += 7
    elif issue_count >= 1:
        score += 4

    # First-time contributor merge rate (10 pts)
    ftc_merge_rate = first_time_pr_data.get("first_time_merge_rate", 0)
    if ftc_merge_rate >= 70:
        score += 10
    elif ftc_merge_rate >= 50:
        score += 7
    elif ftc_merge_rate >= 30:
        score += 4
    else:
        score += 2

    # Small PR merge time (5 pts)
    small_prs = pr_size_data[pr_size_data["size_bucket"].str.contains("XS|S", na=False)]
    if not small_prs.empty:
        avg_merge_hours = small_prs["avg_merge_hours"].mean()
        if avg_merge_hours <= 48:
            score += 5
        elif avg_merge_hours <= 168:  # 1 week
            score += 3
        else:
            score += 1

    score = min(score, max_score)

    if score >= 20:
        label = "Low Barrier"
        detail = "Very welcoming to new contributors."
    elif score >= 12:
        label = "Moderate Barrier"
        detail = "Some friction for newcomers, but manageable."
    else:
        label = "High Barrier"
        detail = "May be challenging for first-time contributors."

    return {
        "score": score,
        "max": max_score,
        "label": label,
        "detail": detail,
    }


def score_time_commitment(
    user_profile: dict,
    conn: sqlite3.Connection,
    repo_id: int,
    days: int = 90
) -> dict:
    """
    Score time commitment match (0-25 pts).

    Args:
        user_profile: User profile dict
        conn: SQLite connection
        repo_id: Repository ID
        days: Time window in days

    Returns:
        dict: {'score': int, 'max': 25, 'label': str, 'detail': str}
    """
    score = 0
    max_score = 25

    weekly_hours = user_profile.get("weekly_hours_available", 5)
    pr_size_data = get_pr_size_analysis(conn, repo_id)

    if pr_size_data.empty:
        return {
            "score": 15,  # Neutral score
            "max": max_score,
            "label": "Unknown",
            "detail": "Not enough data to assess time commitment.",
        }

    # Calculate average PR size
    total_prs = pr_size_data["total_prs"].sum()
    if total_prs == 0:
        avg_complexity = "medium"
    else:
        # Simple heuristic based on size distribution
        large_pr_pct = (
            pr_size_data[pr_size_data["size_bucket"].str.contains("L|XL", na=False)]["total_prs"].sum()
            / total_prs * 100
        )

        if large_pr_pct > 50:
            avg_complexity = "high"
        elif large_pr_pct > 25:
            avg_complexity = "medium"
        else:
            avg_complexity = "low"

    # Match hours to complexity
    if weekly_hours <= 5:
        if avg_complexity == "low":
            score = 25
            label = "Perfect Match"
            detail = "PRs are small and fit your available time."
        elif avg_complexity == "medium":
            score = 15
            label = "Tight Fit"
            detail = "PRs may require focused time blocks."
        else:
            score = 8
            label = "Time Mismatch"
            detail = "PRs are large and may exceed your availability."
    elif weekly_hours <= 15:
        if avg_complexity == "medium":
            score = 25
            label = "Perfect Match"
            detail = "PR complexity matches your availability."
        else:
            score = 18
            label = "Good Match"
            detail = "You have enough time for most PRs."
    else:  # > 15 hours
        score = 25
        label = "Ample Time"
        detail = "You have plenty of time for any PR size."

    score = min(score, max_score)

    return {
        "score": score,
        "max": max_score,
        "label": label,
        "detail": detail,
    }


def get_grade(score: int) -> tuple[str, str]:
    """
    Convert numeric score to letter grade and recommendation.

    Args:
        score: Total score (0-100)

    Returns:
        tuple: (grade, recommendation)
    """
    if score >= 80:
        return "A", "Excellent fit. Start contributing today!"
    elif score >= 65:
        return "B", "Good fit. A few things to consider."
    elif score >= 50:
        return "C", "Moderate fit. Read the codebase first."
    elif score >= 35:
        return "D", "Challenging fit. Be prepared for friction."
    else:
        return "F", "Poor fit. Consider a different repo."


def calculate_compatibility_score(user_profile: dict, conn: sqlite3.Connection, repo_id: int) -> dict:
    """
    Calculate overall compatibility score (0-100) with detailed breakdown.

    Args:
        user_profile: User profile dict with keys:
            - tech_stack: list[str]
            - experience_level: str
            - contribution_type: list[str]
            - weekly_hours_available: int
            - interests: list[str]
            - has_open_source_exp: bool
            - comfortable_with_reviews: bool
            - prefers_active_community: bool
        conn: SQLite connection
        repo_id: Repository ID

    Returns:
        dict: Complete compatibility analysis
    """
    logger.info("Calculating compatibility score...")

    # Get repo metadata
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM repositories WHERE id = ?", (repo_id,))
    repo_row = cursor.fetchone()
    repo_meta = dict(repo_row) if repo_row else {}

    # Calculate dimension scores
    tech = score_tech_alignment(user_profile, repo_meta, conn, repo_id)
    community = score_community_fit(user_profile, conn, repo_id)
    entry = score_entry_barrier(user_profile, conn, repo_id)
    time = score_time_commitment(user_profile, conn, repo_id)

    # Total score
    total_score = tech["score"] + community["score"] + entry["score"] + time["score"]
    grade, recommendation = get_grade(total_score)

    # Generate strengths
    strengths = []
    if tech["score"] >= 15:
        strengths.append(f"✓ {tech['label']}: {tech['detail']}")
    if community["score"] >= 15:
        strengths.append(f"✓ {community['label']}: {community['detail']}")
    if entry["score"] >= 15:
        strengths.append(f"✓ {entry['label']}: {entry['detail']}")
    if time["score"] >= 15:
        strengths.append(f"✓ {time['label']}: {time['detail']}")

    # Generate concerns
    concerns = []
    if tech["score"] < 15:
        concerns.append(f"⚠ {tech['label']}: {tech['detail']}")
    if community["score"] < 15:
        concerns.append(f"⚠ {community['label']}: {community['detail']}")
    if entry["score"] < 15:
        concerns.append(f"⚠ {entry['label']}: {entry['detail']}")
    if time["score"] < 15:
        concerns.append(f"⚠ {time['label']}: {time['detail']}")

    # Generate action items
    action_items = []
    if grade in ["A", "B"]:
        action_items.append("→ Read the CONTRIBUTING.md file")
        action_items.append("→ Browse open issues and find one that interests you")
        action_items.append("→ Introduce yourself in an issue or discussion")
    elif grade == "C":
        action_items.append("→ Clone the repo and run it locally first")
        action_items.append("→ Read through recent PRs to understand the review culture")
        action_items.append("→ Start with documentation improvements")
    else:
        action_items.append("→ Look for repos with a higher compatibility score")
        action_items.append("→ Build your skills in the repo's primary language first")
        action_items.append("→ Consider contributing to more beginner-friendly projects")

    result = {
        "total_score": total_score,
        "grade": grade,
        "recommendation": recommendation,
        "breakdown": {
            "tech_alignment": tech,
            "community_fit": community,
            "entry_barrier": entry,
            "time_commitment": time,
        },
        "strengths": strengths,
        "concerns": concerns,
        "action_items": action_items,
    }

    logger.info(f"Compatibility score calculated: {total_score}/100 (Grade: {grade})")
    return result
