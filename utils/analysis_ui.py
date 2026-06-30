"""Shared UI components for resume analysis dashboards."""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, Optional


def format_analysis_text(text: str) -> str:
    """Normalize AI output into clean markdown with bullet points."""
    if not text or not text.strip():
        return "_No analysis available._"

    lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith(("-", "•", "*", "–")):
            cleaned = line.lstrip("-•*– ").strip()
            lines.append(f"- {cleaned}")
        elif line[0].isdigit() and "." in line[:4]:
            lines.append(f"\n**{line}**")
        elif line.endswith(":") and len(line) < 80:
            lines.append(f"\n**{line}**")
        else:
            lines.append(line)
    return "\n".join(lines)


def _score_color(total: float) -> str:
    if total >= 85:
        return "#4caf50"
    if total >= 70:
        return "#ff9800"
    if total >= 50:
        return "#ff5722"
    return "#f44336"


def _interpret_score(total: float) -> tuple:
    if total >= 85:
        return "success", "Your resume is well-optimized for ATS systems."
    if total >= 70:
        return "warning", "Your resume meets basic ATS requirements but has room for improvement."
    if total >= 50:
        return "warning", "Your resume needs significant improvements before it is competitive for this role."
    return "error", "Your resume is incomplete or misaligned for this role. Add core skills and role-specific content."


def render_ats_score_tab(scores: Dict[str, Any], target_role: str) -> None:
    """Render centered ATS score breakdown."""
    total_score = scores.get("total_score", 0)
    role_label = target_role or "the specified role"

    st.markdown(
        f"""
        <div class="ats-score-container">
            <p class="ats-score-label">Overall ATS Score</p>
            <h2 class="ats-score-value" style="color:{_score_color(total_score)};">{total_score:.0f}%</h2>
            <p class="ats-score-role">Evaluated for: <strong>{role_label}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    components = [
        ("Format & Structure", "format_score", 15),
        ("Content Quality", "content_score", 25),
        ("Skills Coverage", "skills_score", 25),
        ("Role & Keyword Match", "keyword_score", 25),
        ("Readability", "readability_score", 10),
    ]

    st.markdown("### Score Breakdown")
    st.markdown(
        '<div class="score-breakdown-wrapper"><div class="score-breakdown-grid">',
        unsafe_allow_html=True,
    )

    for label, key, maximum in components:
        value = scores.get(key, 0)
        pct = min(100, (value / maximum) * 100) if maximum else 0
        st.markdown(
            f"""
            <div class="score-breakdown-card">
                <div class="score-breakdown-title">{label}</div>
                <div class="score-breakdown-value">{value:.1f} <span>/ {maximum}</span></div>
                <div class="score-breakdown-bar">
                    <div class="score-breakdown-fill" style="width:{pct:.0f}%;"></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div></div>", unsafe_allow_html=True)

    feedback = scores.get("feedback") or []
    if feedback:
        st.markdown("### Key Findings")
        for item in feedback[:8]:
            st.markdown(f"- {item}")

    priority = scores.get("improvement_priority") or []
    if priority:
        st.markdown("### Priority Actions")
        for action, level in priority[:5]:
            st.markdown(f"- **{level}**: {action}")

    level, message = _interpret_score(total_score)
    getattr(st, level)(message)


def render_profile_tab(analysis_text: str, target_role: str) -> None:
    st.subheader("Profile Analysis")
    st.markdown(f"**Target Role:** {target_role or 'Not specified'}")
    st.markdown(format_analysis_text(analysis_text))


def render_skills_tab(
    skills_analysis: str,
    target_role: str,
    skills_data: Dict[str, list],
) -> None:
    st.subheader("Skills Analysis")
    st.markdown(f"**Target Role:** {target_role or 'Not specified'}")

    if not any(skills_data.values()):
        st.error(
            "No core technical skills detected. For this role, add programming languages, "
            "frameworks, and tools that match the job requirements."
        )
    else:
        st.markdown("#### Detected Skills")
        category_labels = {
            "programming_languages": "Programming Languages",
            "frameworks_libraries": "Frameworks & Libraries",
            "tools_technologies": "Tools & Technologies",
            "soft_skills": "Professional Skills",
        }
        for key, label in category_labels.items():
            items = sorted(skills_data.get(key, []))
            if items:
                st.markdown(f"**{label}**")
                for skill in items:
                    st.markdown(f"- {skill}")

    st.markdown("#### Role-Focused Assessment")
    st.markdown(format_analysis_text(skills_analysis))


def render_optimization_tab(ats_analysis: str, scores: Optional[Dict[str, Any]], target_role: str) -> None:
    st.subheader("ATS Optimization")
    st.markdown(f"**Target Role:** {target_role or 'Not specified'}")
    if scores:
        col1, col2, col3 = st.columns(3)
        col1.metric("Overall Score", f"{scores.get('total_score', 0):.0f}%")
        col2.metric("Skills Match", f"{scores.get('skills_score', 0):.0f}/25")
        col3.metric("Role Match", f"{scores.get('keyword_score', 0):.0f}/25")
    st.markdown(format_analysis_text(ats_analysis))


def render_summary_tab(scores: Dict[str, Any], target_role: str, analysis: Dict[str, str]) -> None:
    st.subheader("Executive Summary")
    total = scores.get("total_score", 0)
    st.markdown(f"**Target Role:** {target_role or 'Not specified'}")
    st.markdown(f"**Overall ATS Score:** {total:.0f}%")

    st.markdown("#### Score Summary")
    summary_items = [
        ("Content Quality", scores.get("content_score", 0), 25),
        ("Skills Coverage", scores.get("skills_score", 0), 25),
        ("Role & Keyword Match", scores.get("keyword_score", 0), 25),
        ("Format & Structure", scores.get("format_score", 0), 15),
        ("Readability", scores.get("readability_score", 0), 10),
    ]
    for label, value, maximum in summary_items:
        st.markdown(f"- **{label}:** {value:.1f} / {maximum}")

    missing = scores.get("missing_role_skills") or []
    if missing:
        st.markdown("#### Missing Role-Critical Skills")
        for skill in missing[:10]:
            st.markdown(f"- {skill}")

    st.markdown("#### Profile Highlights")
    st.markdown(format_analysis_text(analysis.get("profile_analysis", "")))


def render_visualization_tab(scores: Dict[str, Any], skills_data: Dict[str, list]) -> None:
    st.subheader("Analysis Visualization")

    categories = ["Content", "Skills", "Role Match", "Format", "Readability"]
    values = [
        scores.get("content_score", 0),
        scores.get("skills_score", 0),
        scores.get("keyword_score", 0),
        scores.get("format_score", 0),
        scores.get("readability_score", 0),
    ]

    col1, col2 = st.columns(2)
    with col1:
        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(r=values, theta=categories, fill="toself", name="Your Resume")
        )
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 25])),
            showlegend=False,
            title="Score Distribution",
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        total_score = scores.get("total_score", 0)
        fig_gauge = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=total_score,
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": _score_color(total_score)},
                    "steps": [
                        {"range": [0, 40], "color": "#ffcdd2"},
                        {"range": [40, 60], "color": "#ffe0b2"},
                        {"range": [60, 80], "color": "#bbdefb"},
                        {"range": [80, 100], "color": "#c8e6c9"},
                    ],
                    "threshold": {"line": {"color": "red", "width": 3}, "thickness": 0.75, "value": 85},
                },
                title={"text": "Overall ATS Score"},
            )
        )
        st.plotly_chart(fig_gauge, use_container_width=True)

    if any(skills_data.values()):
        labels, counts = [], []
        for key, items in skills_data.items():
            if items:
                labels.append(key.replace("_", " ").title())
                counts.append(len(items))
        if labels:
            fig_skills = go.Figure(data=[go.Pie(labels=labels, values=counts, hole=0.35)])
            fig_skills.update_layout(title="Skills Distribution")
            st.plotly_chart(fig_skills, use_container_width=True)


def render_analysis_dashboard(
    analysis: Dict[str, str],
    scores: Dict[str, Any],
    target_role: str,
    skills_data: Dict[str, list],
) -> None:
    """Render the full six-tab analysis dashboard."""
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "ATS Score",
        "Profile Analysis",
        "Skills Analysis",
        "Optimization",
        "Summary Report",
        "Visualization",
    ])

    with tab1:
        render_ats_score_tab(scores, target_role)
    with tab2:
        render_profile_tab(analysis.get("profile_analysis", ""), target_role)
    with tab3:
        render_skills_tab(analysis.get("skills_analysis", ""), target_role, skills_data)
    with tab4:
        render_optimization_tab(analysis.get("ats_analysis", ""), scores, target_role)
    with tab5:
        render_summary_tab(scores, target_role, analysis)
    with tab6:
        render_visualization_tab(scores, skills_data)
