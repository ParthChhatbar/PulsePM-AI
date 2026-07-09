from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv() -> bool:
        return False

from agents.parser_agent import ParserAgent
from main import analyze_workbook, generate_monthly
from utils.scheduler import start_scheduler
from utils.storage import load_weekly_reports

load_dotenv()


def safe_attr(obj, name: str, default):
    return getattr(obj, name, default)


def safe_list(obj, name: str):
    value = getattr(obj, name, [])
    return value or []

st.set_page_config(page_title="PulsePM AI", page_icon="PulsePM", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #f6f8fb; color: #142238; }
    [data-testid="stSidebar"] { background: #102033; }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p {
        color: #f5f8fb;
    }
    [data-testid="stSidebar"] button {
        background: #ffffff;
        color: #102033 !important;
        border: 1px solid #cbd5e1;
        font-weight: 700;
    }
    [data-testid="stSidebar"] button * {
        color: #102033 !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section {
        background: #ffffff;
        border: 1px solid #cbd5e1;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small {
        color: #102033 !important;
        opacity: 1 !important;
    }
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
        background: #eef2f7;
        color: #102033 !important;
    }
    [data-testid="stSidebar"] [data-testid="stToggle"] * {
        color: #f5f8fb !important;
        opacity: 1 !important;
    }
    div[data-testid="stMetric"] {
        background: #ffffff; border: 1px solid #d9e2ec; padding: 14px; border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, .06);
    }
    .block-container { padding-top: 1.2rem; max-width: 1400px; }
    .advisor-panel {
        background: #ffffff; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px;
        box-shadow: 0 1px 3px rgba(15, 23, 42, .08); margin-bottom: 16px;
    }
    .risk-red { color: #b42318; font-weight: 700; }
    .risk-amber { color: #b7791f; font-weight: 700; }
    .risk-green { color: #087443; font-weight: 700; }
    h1, h2, h3 { color: #132238; }
    </style>
    """,
    unsafe_allow_html=True,
)

OUTPUT = Path(os.getenv("OUTPUT_FOLDER", "output"))
DATA = Path(os.getenv("INPUT_FOLDER", "data"))
DATA.mkdir(exist_ok=True)

st.title("PulsePM AI")
st.caption("AI PMO Executive Advisor for project health, risk, trends and leadership decisions")

with st.sidebar:
    st.header("Controls")
    uploaded = st.file_uploader("Upload Excel", type=["xlsx", "xlsm", "xls"])
    run_weekly = st.button("Run Weekly Analysis", use_container_width=True)
    run_monthly = st.button("Generate Monthly Report", use_container_width=True)
    run_ppt = st.button("Generate PPT", use_container_width=True)
    scheduler_enabled = st.toggle("Scheduler", value=False)
    if scheduler_enabled and "scheduler" not in st.session_state:
        st.session_state.scheduler = start_scheduler(DATA, OUTPUT)
        st.success("Monday scheduler started")

active_report = None
if uploaded:
    saved_path = DATA / uploaded.name
    saved_path.write_bytes(uploaded.getbuffer())
    with st.expander("Workbook Discovery", expanded=False):
        st.json(ParserAgent().inspect(saved_path))
    if run_weekly:
        with st.spinner("Running executive analysis..."):
            active_report = analyze_workbook(saved_path, OUTPUT)
        st.success(f"Weekly report saved: {active_report.scoring.rag} ({active_report.scoring.score})")
elif run_weekly:
    st.warning("Upload an Excel workbook first.")

if run_monthly or run_ppt:
    with st.spinner("Generating monthly synthesis and PPT..."):
        synthesis = generate_monthly(OUTPUT, create_ppt=True)
    st.success("Monthly executive outputs generated.")
    st.json(synthesis.model_dump(mode="json"))

reports = [report for report in load_weekly_reports(OUTPUT) if report.project.project_name != "Unknown Project"]
upgraded_reports = [report for report in reports if safe_attr(report.features, "data_completeness_score", 0.0) > 0]
if upgraded_reports:
    reports = upgraded_reports
if active_report:
    reports = [active_report] + [r for r in reports if r.report_id != active_report.report_id]

if not reports:
    st.info("Upload a project workbook and run weekly analysis to populate the advisor.")
    st.stop()

latest = active_report or sorted(reports, key=lambda r: r.generated_at)[-1]
risk_class = {"Red": "risk-red", "Amber": "risk-amber", "Green": "risk-green"}.get(latest.scoring.rag, "")
st.subheader(latest.project.project_name)
st.markdown(
    f"<div class='advisor-panel'><span class='{risk_class}'>Risk Level: {latest.scoring.rag}</span><br>{latest.reasoning.executive_summary}</div>",
    unsafe_allow_html=True,
)

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Health Score", f"{latest.scoring.score}/100")
col2.metric("Completion", f"{latest.features.completion_percent}%")
col3.metric("Confidence", f"{latest.scoring.confidence}%")
col4.metric("Data Complete", f"{safe_attr(latest.features, 'data_completeness_score', 0.0)}%")
col5.metric("Open Risks", latest.features.open_risks)
col6.metric("Late Tasks", latest.features.late_tasks)

tab1, tab2, tab3, tab4 = st.tabs(["Executive View", "Risks & Milestones", "Trend", "Evidence"])

with tab1:
    left, right = st.columns([1.1, 1])
    with left:
        st.markdown("### Key Findings")
        for item in safe_list(latest.reasoning, "key_findings"):
            st.write(f"- {item}")
        st.markdown("### Root Causes")
        for item in safe_list(latest.reasoning, "root_cause_analysis"):
            st.write(f"- {item}")
    with right:
        st.markdown("### Business Impact")
        st.write(latest.reasoning.business_impact)
        st.markdown("### Leadership Recommendations")
        for item in latest.reasoning.recommendations:
            st.write(f"- {item}")
        st.markdown("### Confidence")
        st.write(safe_attr(latest.reasoning, "data_quality_note", "") or safe_attr(latest.features, "confidence_explanation", "Confidence details are unavailable for this legacy report."))

with tab2:
    left, right = st.columns([1, 1])
    with left:
        st.markdown("### Top Risks")
        risk_df = pd.DataFrame(safe_list(latest.features, "risk_register")[:8])
        if not risk_df.empty:
            st.dataframe(risk_df, use_container_width=True, hide_index=True)
        else:
            st.info("No risk register entries found.")
    with right:
        st.markdown("### Upcoming Milestones")
        milestone_df = pd.DataFrame(safe_list(latest.features, "upcoming_milestones"))
        if not milestone_df.empty:
            st.dataframe(milestone_df, use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming milestones identified.")
    st.markdown("### Positive Signals")
    for item in safe_list(latest.features, "positive_signals") or ["No positive commentary signal was captured."]:
        st.write(f"- {item}")

with tab3:
    project_reports = [r for r in reports if r.project.project_name == latest.project.project_name]
    trend_df = pd.DataFrame(
        [
            {
                "Generated": r.generated_at,
                "Week": safe_attr(r, "week_number", 0),
                "Project": r.project.project_name,
                "Score": r.scoring.score,
                "Completion": r.features.completion_percent,
                "Open Risks": r.features.open_risks,
                "Late Tasks": r.features.late_tasks,
            }
            for r in project_reports
        ]
    )
    if not trend_df.empty:
        st.plotly_chart(px.line(trend_df, x="Generated", y="Score", markers=True, title="Health Timeline"), use_container_width=True)
        st.plotly_chart(px.line(trend_df, x="Generated", y=["Completion", "Open Risks", "Late Tasks"], markers=True, title="Historical Trend"), use_container_width=True)
    if safe_attr(latest, "trend", None):
        st.markdown(f"### Trend Status: {latest.trend.status}")
        for item in latest.trend.insights:
            st.write(f"- {item}")
        if latest.trend.recurring_risks:
            st.markdown("### Recurring Risks")
            for item in latest.trend.recurring_risks:
                st.write(f"- {item}")

with tab4:
    left, right = st.columns([1, 1])
    with left:
        st.plotly_chart(
            px.pie(
                names=list(latest.features.health_distribution.keys()),
                values=list(latest.features.health_distribution.values()),
                title="Schedule Health Distribution",
                hole=0.45,
            ),
            use_container_width=True,
        )
    with right:
        status_df = pd.DataFrame(
            {"Status": list(latest.features.task_status_distribution.keys()), "Count": list(latest.features.task_status_distribution.values())}
        )
        st.plotly_chart(px.bar(status_df, x="Status", y="Count", title="Task Status"), use_container_width=True)
    st.markdown("### Interpreted Comments")
    comments_df = pd.DataFrame(safe_list(latest.features, "interpreted_comments"))
    if not comments_df.empty:
        st.dataframe(comments_df, use_container_width=True, hide_index=True)
    st.markdown("### Missing Data Handled")
    for item in latest.reasoning.missing_information or ["No material missing data was detected."]:
        st.write(f"- {item}")

download_col1, download_col2, download_col3 = st.columns(3)
if latest.json_path and Path(latest.json_path).exists():
    download_col1.download_button("Download JSON", Path(latest.json_path).read_bytes(), file_name=Path(latest.json_path).name)
if latest.markdown_path and Path(latest.markdown_path).exists():
    download_col2.download_button("Download Markdown", Path(latest.markdown_path).read_bytes(), file_name=Path(latest.markdown_path).name)
latest_ppt = sorted((OUTPUT / "ppt").glob("*.pptx"))
if latest_ppt:
    download_col3.download_button("Download Latest PPT", latest_ppt[-1].read_bytes(), file_name=latest_ppt[-1].name)
