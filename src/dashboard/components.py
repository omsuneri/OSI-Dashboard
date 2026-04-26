import streamlit as st
import pandas as pd
from typing import Optional


def metric_card(label: str, value: str, delta: Optional[str] = None, color: str = "blue"):
    """
    Display a metric card with optional delta.

    Args:
        label: Metric label
        value: Metric value (formatted string)
        delta: Optional delta value
        color: Color theme (blue, green, red, orange)
    """
    if delta:
        st.metric(label=label, value=value, delta=delta)
    else:
        st.metric(label=label, value=value)


def progress_bar_labeled(label: str, value: float, max_val: float, color: str = "blue"):
    """
    Display a labeled progress bar.

    Args:
        label: Progress bar label
        value: Current value
        max_val: Maximum value
        color: Color theme
    """
    percentage = (value / max_val * 100) if max_val > 0 else 0
    st.markdown(f"**{label}**")
    st.progress(min(percentage / 100, 1.0))
    st.caption(f"{value:.1f} / {max_val:.1f} ({percentage:.1f}%)")


def dataframe_styled(df: pd.DataFrame, highlight_col: Optional[str] = None):
    """
    Display a styled DataFrame.

    Args:
        df: DataFrame to display
        highlight_col: Optional column to highlight
    """
    if df.empty:
        st.info("No data available")
        return

    if highlight_col and highlight_col in df.columns:
        st.dataframe(
            df.style.background_gradient(subset=[highlight_col], cmap="YlGn"),
            use_container_width=True,
        )
    else:
        st.dataframe(df, use_container_width=True)


def section_header(title: str, subtitle: Optional[str] = None):
    """
    Display a section header with optional subtitle.

    Args:
        title: Section title
        subtitle: Optional subtitle
    """
    st.markdown(f"### {title}")
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")


def info_callout(text: str, type: str = "info"):
    """
    Display an information callout.

    Args:
        text: Callout text
        type: Callout type (info, warning, success, error)
    """
    if type == "info":
        st.info(text)
    elif type == "warning":
        st.warning(text)
    elif type == "success":
        st.success(text)
    elif type == "error":
        st.error(text)
    else:
        st.info(text)


def sidebar_repo_form():
    """
    Display repository input form in sidebar.

    Returns:
        tuple: (owner, repo) if submitted, else (None, None)
    """
    with st.sidebar:
        st.markdown("### 📊 Repository Analysis")
        repo_input = st.text_input(
            "GitHub Repository",
            placeholder="e.g. sugarlabs/musicblocks",
            help="Enter owner/repo format"
        )

        analyze_button = st.button("🚀 Analyze Repository", type="primary", use_container_width=True)

        if analyze_button and repo_input:
            if "/" in repo_input:
                owner, repo = repo_input.split("/", 1)
                return owner.strip(), repo.strip()
            else:
                st.error("Invalid format. Use: owner/repo")
                return None, None

        return None, None


def loading_message(message: str = "Loading data..."):
    """
    Display a loading message.

    Args:
        message: Loading message text
    """
    st.info(f"⏳ {message}")
