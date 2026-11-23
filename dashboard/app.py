import os

import pandas as pd
import streamlit as st

from dqtk.storage.run_history import RunHistory

st.set_page_config(page_title="dqtk — data quality dashboard", layout="wide")

DSN = os.environ.get("DQTK_STORAGE_DSN", "postgresql+psycopg2://dqtk:dqtk@postgres:5432/dqtk")

st.title("Data Quality Toolkit — run history")
st.caption(f"Reading run history from `{DSN}`")

history = RunHistory(DSN)
runs = history.recent_runs(limit=200)

if not runs:
    st.info("No check runs yet. Run `dqtk run --config config.yml` to populate this dashboard.")
    st.stop()

run_rows = [
    {
        "run_id": r.id,
        "table": r.table_name,
        "started_at": r.started_at,
        "finished_at": r.finished_at,
        "status": r.status,
    }
    for r in runs
]
runs_df = pd.DataFrame(run_rows).sort_values("started_at")

status_counts = runs_df["status"].value_counts()
cols = st.columns(len(status_counts) or 1)
for col, (status, count) in zip(cols, status_counts.items()):
    col.metric(status.upper(), count)

st.subheader("Run status over time")
chart_df = runs_df.set_index("started_at")[["status"]].copy()
chart_df["value"] = 1
pivot = chart_df.pivot_table(index="started_at", columns="status", values="value", aggfunc="sum").fillna(0)
st.bar_chart(pivot)

st.subheader("Table filter")
table_names = sorted(runs_df["table"].unique())
selected_table = st.selectbox("Table", ["(all)"] + table_names)

st.subheader("Recent runs")
display_df = runs_df if selected_table == "(all)" else runs_df[runs_df["table"] == selected_table]
st.dataframe(display_df.sort_values("started_at", ascending=False), use_container_width=True)

st.subheader("Check results for a run")
run_id_options = display_df.sort_values("started_at", ascending=False)["run_id"].tolist()
if run_id_options:
    selected_run_id = st.selectbox("Run ID", run_id_options)
    selected_run = next(r for r in runs if r.id == selected_run_id)
    result_rows = [
        {"check": res.check_name, "status": res.status, "message": res.message}
        for res in selected_run.results
    ]
    st.table(pd.DataFrame(result_rows))

history.close()
