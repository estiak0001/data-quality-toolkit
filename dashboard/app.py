import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dqtk.storage.run_history import RunHistory

st.set_page_config(page_title="dqtk — data quality dashboard", page_icon="◆", layout="wide")

# Status palette — fixed roles, never reused for anything else, always
# paired with an icon + label rather than color alone.
STATUS_STYLE = {
    "pass": ("done", "#0ca30c"),
    "warn": ("warn", "#fab219"),
    "fail": ("fail", "#ec835a"),
    "error": ("error", "#d03b3b"),
}
STATUS_ORDER = ["pass", "warn", "fail", "error"]
SEQUENTIAL_BLUE = "#2a78d6"


def status_badge(status: str) -> str:
    icon, color = STATUS_STYLE.get(status, ("?", "#898781"))
    return f'<span style="color:{color}; font-weight:600;">{icon} {status}</span>'


def style_status_column(df: pd.DataFrame, column: str = "status"):
    def _color(val):
        _, color = STATUS_STYLE.get(val, ("?", "#898781"))
        return f"color: {color}; font-weight: 600;"

    return df.style.map(_color, subset=[column])


def empty_state(message: str) -> None:
    st.info(message)


DSN = os.environ.get("DQTK_STORAGE_DSN", "postgresql+psycopg2://dqtk:dqtk@postgres:5432/dqtk")

st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }
    </style>
    <div style="padding: 1.25rem 1.5rem; border-radius: 10px; background: #0b0b0b; margin-bottom: 1.5rem;">
        <div style="color: #f0efec; font-size: 1.6rem; font-weight: 700;">dqtk — data quality dashboard</div>
        <div style="color: #c3c2b7; font-size: 0.9rem; margin-top: 0.25rem;">
            Freshness, row-count, null-rate and schema-drift checks, run on a schedule and tracked over time.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

history = RunHistory(DSN)
runs = history.recent_runs(limit=500)

if not runs:
    empty_state("No check runs yet. Run `dqtk run --config config.yml` to populate this dashboard.")
    st.stop()

runs_df = pd.DataFrame(
    [
        {
            "run_id": r.id,
            "table": r.table_name,
            "started_at": r.started_at,
            "finished_at": r.finished_at,
            "status": r.status,
        }
        for r in runs
    ]
).sort_values("started_at")

long_df = pd.DataFrame(
    [
        {
            "run_id": r.id,
            "table": r.table_name,
            "started_at": r.started_at,
            "check_name": res.check_name,
            "status": res.status,
            "message": res.message,
            "details": res.details,
        }
        for r in runs
        for res in r.results
    ]
).sort_values("started_at")

# --- Sidebar: global filters -------------------------------------------
with st.sidebar:
    st.header("Filters")
    all_tables = sorted(long_df["table"].unique())
    all_checks = sorted(long_df["check_name"].unique())
    all_statuses = [s for s in STATUS_ORDER if s in long_df["status"].unique()]

    selected_tables = st.multiselect("Tables", all_tables, default=all_tables)
    selected_checks = st.multiselect("Check types", all_checks, default=all_checks)
    selected_statuses = st.multiselect("Status", all_statuses, default=all_statuses)

filtered = long_df[
    long_df["table"].isin(selected_tables)
    & long_df["check_name"].isin(selected_checks)
    & long_df["status"].isin(selected_statuses)
]

tab_overview, tab_freshness, tab_rowcount, tab_nulls, tab_schema, tab_explorer = st.tabs(
    ["Overview", "Freshness", "Row Counts", "Null Rates", "Schema Drift", "Run Explorer"]
)

# =============================================================================
# Overview
# =============================================================================
with tab_overview:
    if filtered.empty:
        empty_state("No check results match the current filters.")
    else:
        pass_rate = (filtered["status"] == "pass").mean() * 100
        latest_per_check = filtered.sort_values("started_at").groupby(["table", "check_name"]).tail(1)
        issues = latest_per_check[latest_per_check["status"] != "pass"]

        kpi_cols = st.columns(4)
        kpi_cols[0].metric("Check results", len(filtered))
        kpi_cols[1].metric("Pass rate", f"{pass_rate:.0f}%")
        kpi_cols[2].metric("Tables monitored", filtered["table"].nunique())
        kpi_cols[3].metric("Open issues", len(issues), delta=None)

        g1, g2 = st.columns([1, 2])
        with g1:
            st.subheader("Overall health")
            gauge_color = "#0ca30c" if pass_rate >= 90 else "#fab219" if pass_rate >= 70 else "#d03b3b"
            fig = go.Figure(
                go.Indicator(
                    mode="gauge+number",
                    value=pass_rate,
                    number={"suffix": "%"},
                    gauge={
                        "axis": {"range": [0, 100]},
                        "bar": {"color": gauge_color},
                        "steps": [
                            {"range": [0, 70], "color": "rgba(208,59,59,0.15)"},
                            {"range": [70, 90], "color": "rgba(250,178,25,0.15)"},
                            {"range": [90, 100], "color": "rgba(12,163,12,0.15)"},
                        ],
                    },
                )
            )
            fig.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=10))
            st.plotly_chart(fig)

        with g2:
            st.subheader("Check results by status")
            status_counts = filtered["status"].value_counts().reindex(STATUS_ORDER).dropna()
            donut = go.Figure(
                go.Pie(
                    labels=status_counts.index,
                    values=status_counts.values,
                    hole=0.55,
                    marker=dict(colors=[STATUS_STYLE[s][1] for s in status_counts.index]),
                )
            )
            donut.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=10))
            st.plotly_chart(donut)

        st.subheader("Check results over time")
        time_df = filtered.copy()
        time_df["date"] = pd.to_datetime(time_df["started_at"]).dt.floor("min")
        timeline = (
            time_df.groupby(["date", "status"]).size().reset_index(name="count")
        )
        area = px.area(
            timeline,
            x="date",
            y="count",
            color="status",
            category_orders={"status": STATUS_ORDER},
            color_discrete_map={s: STATUS_STYLE[s][1] for s in STATUS_ORDER},
        )
        area.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=10), legend_title_text="")
        st.plotly_chart(area)

        st.subheader("Needs attention")
        if issues.empty:
            st.success("Every table's latest check result is passing.")
        else:
            issues_display = issues[["table", "check_name", "status", "message", "started_at"]].sort_values(
                "started_at", ascending=False
            )
            st.dataframe(style_status_column(issues_display), width="stretch", hide_index=True)

# =============================================================================
# Freshness
# =============================================================================
with tab_freshness:
    fresh_df = filtered[filtered["check_name"] == "freshness"].copy()
    if fresh_df.empty:
        empty_state("No freshness check results match the current filters.")
    else:
        fresh_df["age_minutes"] = fresh_df["details"].apply(lambda d: d.get("age_minutes"))
        fresh_df["threshold_minutes"] = fresh_df["details"].apply(lambda d: d.get("threshold_minutes"))

        for table in sorted(fresh_df["table"].unique()):
            t_df = fresh_df[fresh_df["table"] == table].sort_values("started_at")
            latest = t_df.iloc[-1]
            st.markdown(f"**{table}** — {status_badge(latest['status'])}", unsafe_allow_html=True)

            c1, c2 = st.columns([1, 2])
            with c1:
                threshold = latest["threshold_minutes"] or 1
                age = latest["age_minutes"] or 0
                gauge_color = STATUS_STYLE[latest["status"]][1]
                fig = go.Figure(
                    go.Indicator(
                        mode="gauge+number",
                        value=age,
                        number={"suffix": " min"},
                        gauge={
                            "axis": {"range": [0, max(threshold * 2, age * 1.1, 1)]},
                            "bar": {"color": gauge_color},
                            "threshold": {
                                "line": {"color": "#898781", "width": 3},
                                "thickness": 0.85,
                                "value": threshold,
                            },
                        },
                        title={"text": "age vs. threshold (min)"},
                    )
                )
                fig.update_layout(height=220, margin=dict(l=20, r=20, t=40, b=10))
                st.plotly_chart(fig, width="stretch")

            with c2:
                line = px.line(t_df, x="started_at", y="age_minutes", markers=True)
                line.add_hline(
                    y=latest["threshold_minutes"], line_dash="dot", line_color="#898781",
                    annotation_text="threshold",
                )
                line.update_traces(line_color=SEQUENTIAL_BLUE)
                line.update_layout(height=220, margin=dict(l=20, r=20, t=20, b=10), yaxis_title="age (min)")
                st.plotly_chart(line, width="stretch")
            st.divider()

# =============================================================================
# Row Counts
# =============================================================================
with tab_rowcount:
    rc_df = filtered[filtered["check_name"] == "row_count"].copy()
    if rc_df.empty:
        empty_state("No row-count check results match the current filters.")
    else:
        rc_df["current"] = rc_df["details"].apply(lambda d: d.get("current"))
        rc_df["baseline"] = rc_df["details"].apply(lambda d: d.get("baseline"))
        rc_df["threshold"] = rc_df["details"].apply(lambda d: d.get("threshold"))

        for table in sorted(rc_df["table"].unique()):
            t_df = rc_df[rc_df["table"] == table].sort_values("started_at")
            latest = t_df.iloc[-1]
            st.markdown(f"**{table}** — {status_badge(latest['status'])}", unsafe_allow_html=True)

            fig = go.Figure()
            if latest["baseline"] and latest["threshold"]:
                band_upper = t_df["baseline"] * (1 + t_df["threshold"].fillna(0))
                band_lower = t_df["baseline"] * (1 - t_df["threshold"].fillna(0))
                fig.add_trace(go.Scatter(
                    x=pd.concat([t_df["started_at"], t_df["started_at"][::-1]]),
                    y=pd.concat([band_upper, band_lower[::-1]]),
                    fill="toself", fillcolor="rgba(137,135,129,0.15)",
                    line=dict(color="rgba(0,0,0,0)"), name="baseline band", showlegend=True,
                ))
            fig.add_trace(go.Scatter(
                x=t_df["started_at"], y=t_df["current"], mode="lines+markers",
                line=dict(color=SEQUENTIAL_BLUE), name="row count",
            ))
            fig.update_layout(height=260, margin=dict(l=20, r=20, t=10, b=10))
            st.plotly_chart(fig, width="stretch")
            st.divider()

# =============================================================================
# Null Rates
# =============================================================================
with tab_nulls:
    null_df = filtered[filtered["check_name"] == "null_rate"].copy()
    if null_df.empty:
        empty_state("No null-rate check results match the current filters.")
    else:
        null_df["null_rate"] = null_df["details"].apply(lambda d: d.get("null_rate"))
        null_df["threshold"] = null_df["details"].apply(lambda d: d.get("threshold"))

        for table in sorted(null_df["table"].unique()):
            t_df = null_df[null_df["table"] == table].sort_values("started_at")
            latest = t_df.iloc[-1]
            st.markdown(f"**{table}** — {status_badge(latest['status'])}", unsafe_allow_html=True)

            line = px.line(t_df, x="started_at", y="null_rate", markers=True)
            if latest["threshold"] is not None:
                line.add_hline(
                    y=latest["threshold"], line_dash="dot", line_color="#898781",
                    annotation_text="threshold",
                )
            line.update_traces(line_color=SEQUENTIAL_BLUE)
            line.update_layout(height=240, margin=dict(l=20, r=20, t=10, b=10), yaxis_tickformat=".1%")
            st.plotly_chart(line, width="stretch")
            st.divider()

# =============================================================================
# Schema Drift
# =============================================================================
with tab_schema:
    schema_df = filtered[filtered["check_name"] == "schema_drift"].copy()
    if schema_df.empty:
        empty_state("No schema-drift check results match the current filters.")
    else:
        drift_events = schema_df[schema_df["status"] != "pass"].sort_values("started_at", ascending=False)
        st.subheader("Drift events")
        if drift_events.empty:
            st.success("No schema drift detected in the filtered history.")
        else:
            for _, row in drift_events.iterrows():
                with st.expander(f"{row['table']} — {row['status']} — {row['started_at']}", expanded=False):
                    st.markdown(status_badge(row["status"]), unsafe_allow_html=True)
                    st.markdown(row["message"])
                    d = row["details"]
                    cols = st.columns(3)
                    cols[0].write("**Added**")
                    cols[0].write(d.get("added") or "—")
                    cols[1].write("**Removed**")
                    cols[1].write(d.get("removed") or "—")
                    cols[2].write("**Type changed**")
                    cols[2].write(d.get("type_changed") or "—")

        st.subheader("Current schema snapshot")
        for table in sorted(schema_df["table"].unique()):
            latest = schema_df[schema_df["table"] == table].sort_values("started_at").iloc[-1]
            columns = latest["details"].get("columns", {})
            if columns:
                with st.expander(f"{table} ({len(columns)} columns)"):
                    st.table(pd.DataFrame(sorted(columns.items()), columns=["column", "type"]))

# =============================================================================
# Run Explorer
# =============================================================================
with tab_explorer:
    st.subheader("Recent runs")
    display_df = runs_df[runs_df["table"].isin(selected_tables)].sort_values("started_at", ascending=False)
    if display_df.empty:
        empty_state("No runs match the current filters.")
    else:
        st.dataframe(style_status_column(display_df), width="stretch", hide_index=True)

        st.subheader("Check results for a run")
        selected_run_id = st.selectbox("Run ID", display_df["run_id"].tolist())
        selected_run = next(r for r in runs if r.id == selected_run_id)
        for res in selected_run.results:
            with st.expander(f"{res.check_name} — {res.message}", expanded=False):
                st.markdown(f"**{res.check_name}** — {status_badge(res.status)}", unsafe_allow_html=True)
                st.write(res.message)
                if res.details:
                    st.json(res.details)

history.close()
