from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from upkie_mujoco_course.course.dashboard_data import build_dashboard_summary
from upkie_mujoco_course.course.dashboard_data import collect_chapter_evidence
from upkie_mujoco_course.course.dashboard_data import is_diagnostic_result
from upkie_mujoco_course.course.dashboard_data import load_experiment_results
from upkie_mujoco_course.course.manifest import load_course_manifest


st.set_page_config(page_title="Upkie 控制实验台", page_icon="U", layout="wide")
st.markdown(
    """
    <style>
    :root { --ink:#17201d; --muted:#68736f; --line:#c9d0cc; --paper:#f4f6f4; --panel:#ffffff; --green:#17745a; --orange:#d36b27; }
    .stApp { background:#f4f6f4; color:var(--ink); font-family:"Bahnschrift","Noto Sans SC",sans-serif; letter-spacing:0; }
    [data-testid="stSidebar"] { background:#17201d; border-right:1px solid #35413d; }
    [data-testid="stSidebar"] * { color:#e8eeeb; }
    [data-testid="stSidebar"] [data-baseweb="select"] { color:#17201d; }
    [data-testid="stSidebar"] [data-baseweb="select"] * { color:#17201d; }
    [data-testid="stSidebar"] input[role="combobox"] { color:#17201d !important; -webkit-text-fill-color:#17201d !important; }
    h1,h2,h3 { letter-spacing:0 !important; font-family:"Bahnschrift SemiCondensed","Noto Sans SC",sans-serif; }
    h1 { font-size:2.1rem !important; margin-bottom:.2rem !important; }
    h2 { font-size:1.25rem !important; border-bottom:1px solid var(--line); padding-bottom:.45rem; }
    [data-testid="stMetric"] { background:var(--panel); border:1px solid var(--line); border-radius:4px; padding:14px 16px; }
    [data-testid="stMetricValue"] { color:var(--green); font-family:"Bahnschrift SemiBold"; }
    .mission { background:#fff; border-left:5px solid var(--orange); padding:18px 20px; margin:10px 0 22px; }
    .mission-id { color:var(--orange); font-weight:700; font-size:.85rem; }
    .mission-title { font-size:1.35rem; font-weight:700; margin:4px 0 8px; }
    .mission-copy { color:var(--muted); line-height:1.75; }
    .status-ready { color:var(--green); font-weight:700; }
    .status-planned { color:var(--muted); font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)

manifest = load_course_manifest()
progress_path = ROOT / "outputs" / "progress" / "progress.json"
progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.exists() else {"chapters": {}}
results = load_experiment_results(ROOT / "outputs")
summary = build_dashboard_summary(manifest, progress, results)

st.sidebar.title("UPKIE LAB")
stage_label = st.sidebar.selectbox(
    "能力阶段",
    [f"{stage['id']} · {stage['title']}" for stage in manifest["stages"]],
)
stage_id = stage_label.split(" · ", 1)[0]
stage_chapters = [chapter for chapter in manifest["chapters"] if chapter["stage"] == stage_id]
chapter_label = st.sidebar.selectbox(
    "任务关卡",
    [f"{chapter['id']} · {chapter['title']}" for chapter in stage_chapters],
)
selected_id = chapter_label.split(" · ", 1)[0]
selected = next(chapter for chapter in stage_chapters if chapter["id"] == selected_id)

st.title("具身智能运动控制实验台")
st.caption(f"课程版本 {manifest['version']} · 物理、代码与证据共同验收")

metric_columns = st.columns(5)
metric_columns[0].metric("总关卡", summary["total_chapters"])
metric_columns[1].metric("已开放", summary["ready_chapters"])
metric_columns[2].metric("已有证据", summary["completed_chapters"])
metric_columns[3].metric("待补证据", summary.get("opened_no_evidence", 0))
completion = 100.0 * summary["completed_chapters"] / summary["total_chapters"]
metric_columns[4].metric("证据完成率", f"{completion:.1f}%")

status_class = "status-ready" if selected["status"] == "ready" else "status-planned"
status_text = "可执行" if selected["status"] == "ready" else "待建设"
st.markdown(
    f"""
    <section class="mission">
      <div class="mission-id">MISSION {selected['id']} · <span class="{status_class}">{status_text}</span></div>
      <div class="mission-title">{selected['title']}</div>
      <div class="mission-copy">{selected['mission']}</div>
    </section>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([1.15, 1])
with left:
    st.subheader("阶段证据")
    labels = [item["title"] for item in summary["stages"]]
    complete_values = [item["completed"] for item in summary["stages"]]
    figure = go.Figure()
    ready_values = [item["ready"] - item["completed"] for item in summary["stages"]]
    not_ready_values = [item["total"] - item["ready"] for item in summary["stages"]]
    figure.add_bar(y=labels, x=complete_values, name="已有证据", orientation="h", marker_color="#17745a")
    figure.add_bar(y=labels, x=ready_values, name="已开放待补证据", orientation="h", marker_color="#d3a85a")
    figure.add_bar(y=labels, x=not_ready_values, name="未开放", orientation="h", marker_color="#c9d0cc")
    figure.update_layout(
        barmode="stack",
        height=430,
        margin=dict(l=10, r=10, t=10, b=90),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        legend=dict(orientation="h", yanchor="top", y=-0.24, xanchor="left", x=0),
        font=dict(family="Bahnschrift, Noto Sans SC", color="#17201d"),
        xaxis=dict(title="关卡数", gridcolor="#e4e8e5"),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(figure, use_container_width=True)
with right:
    st.subheader("当前验收")
    st.code(selected["command"], language="powershell")
    st.markdown(f"**通过条件**<br>{selected['acceptance']}", unsafe_allow_html=True)
    st.markdown(f"**作品集产物**<br><code>{selected['artifact']}</code>", unsafe_allow_html=True)
    evidence = collect_chapter_evidence(progress, results, selected_id)
    if evidence:
        st.markdown("**已有证据**")
        for item in evidence:
            st.markdown(f"- {item}")
    else:
        st.info("尚无验收证据")

acceptance_tab, result_tab, media_tab = st.tabs(["任务验收", "实验结果", "媒体与作品集"])

with acceptance_tab:
    st.markdown(f"**检查点数量**：{len(selected['checkpoints'])}")
    for checkpoint in selected["checkpoints"]:
        st.code(checkpoint["command"], language="powershell")
        st.caption(checkpoint["acceptance"])
    st.markdown(f"[打开本关正文]({selected['tutorial']})")

with result_tab:
    chapter_results = [item for item in results if item.get("chapter_id") == selected_id]
    primary_results = [item for item in chapter_results if not is_diagnostic_result(item)]
    diagnostic_results = [item for item in chapter_results if is_diagnostic_result(item)]
    if primary_results:
        latest = primary_results[-1]
        status = "通过" if latest.get("passed") else "未通过"
        st.markdown(f"**最近结果：{status}** · seed `{latest.get('seed', '未记录')}` · commit `{latest.get('git_commit', '未记录')}`")
        metric_rows = [{"指标": name, "数值": value} for name, value in latest.get("metrics", {}).items()]
        if metric_rows:
            st.dataframe(metric_rows, hide_index=True, use_container_width=True)
        if latest.get("failed_checks"):
            st.error("失败检查：" + "、".join(latest["failed_checks"]))
            st.markdown("诊断路径：先打开对应日志，找到第一处越界指标，再核对配置、单位、seed 和输入数据。")
        else:
            st.success("所有自动检查通过；仍需口头解释设计选择和适用边界。")
        if diagnostic_results:
            st.warning(f"另有 {len(diagnostic_results)} 条故障注入记录，仅用于失败诊断，不计入主验收。")
    else:
        st.info("本关尚无统一实验结果。请先运行关卡检查点。")

with media_tab:
    videos = sorted((ROOT / "outputs" / "videos").glob("*.mp4"))
    if videos:
        for video in videos[-3:]:
            st.video(str(video))
    else:
        st.info("暂无实验视频")
    portfolio = {
        "chapter": selected,
        "progress": progress.get("chapters", {}).get(selected_id, {}),
        "results": [item for item in results if item.get("chapter_id") == selected_id],
    }
    st.download_button(
        "导出本关作品集索引",
        data=json.dumps(portfolio, ensure_ascii=False, indent=2),
        file_name=f"portfolio_{selected_id}.json",
        mime="application/json",
    )
