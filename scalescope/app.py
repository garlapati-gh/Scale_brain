from __future__ import annotations

import sqlite3

import pandas as pd
import plotly.express as px
import streamlit as st

from database import create_database, read_frame
from query_engine import QueryError, ask, is_configured


st.set_page_config(page_title="ScaleScope | Operations Intelligence", page_icon="S", layout="wide")
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
    :root { --ink:#17241f; --muted:#687770; --paper:#f4f6f1; --line:#dfe5dc; --green:#187b5a; --lime:#c7f36b; --coral:#dc765b; }
    html, body, [class*="css"] { font-family: 'Manrope', sans-serif; color:var(--ink); }
    .stApp { background:var(--paper); }
    [data-testid="stSidebar"] { background:#e9eee6; border-right:1px solid var(--line); }
    [data-testid="stMetric"] { background:#fff; border:1px solid var(--line); padding:18px 20px; border-radius:6px; }
    [data-testid="stMetricLabel"] { color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:0; }
    [data-testid="stMetricValue"] { font-weight:700; }
    .eyebrow { font:500 11px 'DM Mono',monospace; text-transform:uppercase; color:var(--green); }
    .masthead { border-bottom:1px solid var(--line); padding:18px 0 22px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:flex-end; }
    .masthead h1 { font-size:32px; line-height:1.1; margin:6px 0 0; letter-spacing:0; }
    .masthead p { color:var(--muted); margin:0; font-size:13px; }
    .mono { font:12px 'DM Mono',monospace; color:var(--muted); }
    div[data-testid="stForm"] { background:white; border:1px solid var(--line); padding:16px; border-radius:6px; }
    div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] button { background:var(--green); color:white; border:0; }
    div.stButton > button { border-radius:4px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_connection() -> sqlite3.Connection:
    return create_database()


connection = get_connection()
today = pd.Timestamp.today().normalize().date().isoformat()
kpis = read_frame(
    connection,
    """SELECT COUNT(*) AS total_tasks,
              SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
              SUM(CASE WHEN status IN ('queued', 'in_progress', 'blocked') AND due_date < :today THEN 1 ELSE 0 END) AS overdue,
              ROUND(AVG(CASE WHEN status = 'completed' THEN quality_score END), 2) AS quality,
              COUNT(DISTINCT CASE WHEN status = 'in_progress' THEN worker_id END) AS active_workers
       FROM tasks""".replace(":today", f"'{today}'"),
)
project_count = read_frame(connection, "SELECT COUNT(*) AS n FROM projects WHERE status IN ('active', 'at_risk')").iloc[0, 0]
status_data = read_frame(connection, "SELECT status, COUNT(*) AS tasks FROM tasks GROUP BY status ORDER BY tasks DESC")
weekly_data = read_frame(
    connection,
    """SELECT strftime('%Y-%W', completed_at) AS week, COUNT(*) AS completed
       FROM tasks WHERE completed_at IS NOT NULL
       GROUP BY week ORDER BY week DESC LIMIT 12""",
).sort_values("week")


with st.sidebar:
    st.markdown("<div class='eyebrow'>SCALESCOPE / INTERNAL</div>", unsafe_allow_html=True)
    st.markdown("### Operations brain")
    st.caption("Mock operational data · refreshed for this session")
    st.divider()
    if is_configured():
        st.success("OpenRouter connected", icon=":material/check_circle:")
    else:
        st.warning("OpenRouter key not configured", icon="🔑")
        st.caption("Set OPENROUTER_API_KEY in your environment to ask questions.")
    st.markdown("**Available data**")
    st.markdown("Projects · tasks · workers · reviews")
    st.markdown("**Try asking**")
    st.caption("Which projects have the most overdue tasks?")
    st.caption("Show average quality score by team.")
    st.caption("Who completed the most tasks this month?")


st.markdown(
    "<div class='masthead'><div><div class='eyebrow'>OPERATIONS INTELLIGENCE / 01</div>"
    "<h1>ScaleScope</h1></div><p>Ask Scale's operational data anything.</p></div>",
    unsafe_allow_html=True,
)
st.markdown("<div class='eyebrow'>LIVE PULSE &nbsp; / &nbsp; MOCK DATASET</div>", unsafe_allow_html=True)

metric_columns = st.columns(5)
metrics = [
    ("Tasks tracked", f"{int(kpis.loc[0, 'total_tasks']):,}"),
    ("Completed", f"{int(kpis.loc[0, 'completed']):,}"),
    ("Past due", f"{int(kpis.loc[0, 'overdue']):,}"),
    ("Avg. quality", f"{float(kpis.loc[0, 'quality']):.2f} / 5"),
    ("Active projects", f"{int(project_count):,}"),
]
for column, (label, value) in zip(metric_columns, metrics):
    column.metric(label, value)

left_chart, right_chart = st.columns([1.1, 1])
with left_chart:
    st.markdown("#### Workload by status")
    status_chart = px.bar(status_data, x="status", y="tasks", color="status", text_auto=True,
                          color_discrete_map={"completed": "#187b5a", "in_progress": "#8eaf45", "queued": "#d6a64a", "blocked": "#dc765b"})
    status_chart.update_layout(showlegend=False, height=270, margin=dict(l=0, r=0, t=10, b=0),
                               paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    status_chart.update_yaxes(title=None, gridcolor="#e5e9e2")
    status_chart.update_xaxes(title=None)
    st.plotly_chart(status_chart, use_container_width=True)
with right_chart:
    st.markdown("#### Weekly completions")
    trend = px.area(weekly_data, x="week", y="completed")
    trend.update_traces(line_color="#187b5a", fillcolor="rgba(24,123,90,0.14)")
    trend.update_layout(showlegend=False, height=270, margin=dict(l=0, r=0, t=10, b=0),
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    trend.update_yaxes(title=None, gridcolor="#e5e9e2")
    trend.update_xaxes(title=None, tickangle=-25)
    st.plotly_chart(trend, use_container_width=True)

st.divider()
st.markdown("<div class='eyebrow'>ASK THE DATA</div>", unsafe_allow_html=True)
with st.form("ask_form"):
    question = st.text_input(
        "Ask a plain-English question",
        placeholder="e.g. Which active projects have the most overdue tasks?",
        label_visibility="collapsed",
    )
    submitted = st.form_submit_button("Explore data", type="primary", use_container_width=True)

if submitted:
    if not is_configured():
        st.error("Add OPENROUTER_API_KEY to your environment, then restart the app to enable questions.")
    elif not question.strip():
        st.info("Type a question first.")
    else:
        with st.spinner("Thinking through the data…"):
            try:
                sql, results = ask(question, connection)
            except QueryError as error:
                st.error(str(error))
            except Exception as error:
                st.error(f"The request could not be completed: {error}")
            else:
                st.markdown("#### Results")
                st.caption(f"{len(results):,} row(s) returned")
                st.dataframe(results, use_container_width=True, hide_index=True)
                numeric_columns = results.select_dtypes(include="number").columns.tolist()
                text_columns = results.select_dtypes(exclude="number").columns.tolist()
                if numeric_columns and text_columns and 1 < len(results) <= 40:
                    chart = px.bar(results, x=text_columns[0], y=numeric_columns[0], text_auto=True)
                    chart.update_layout(height=300, margin=dict(l=0, r=0, t=10, b=0),
                                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(chart, use_container_width=True)
                with st.expander("Generated SQL"):
                    st.code(sql, language="sql")