import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from run import analyze_month_cross, analyze_new_singles, extract_all, fetch_new, latest_month
from storage.db import get_connection

st.set_page_config(page_title="宏观数据解读监控", layout="wide")


@st.cache_data(ttl=300)
def load_reports() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT url, title, pub_date, category, raw_text FROM reports ORDER BY pub_date DESC", conn
    )
    conn.close()
    return df


@st.cache_data(ttl=300)
def load_indicators() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        """SELECT i.name, i.value, i.unit, i.mom_change, i.yoy_change,
                  r.pub_date, r.category, r.title
           FROM indicators i JOIN reports r ON i.report_url = r.url
           ORDER BY r.pub_date""",
        conn,
    )
    conn.close()
    if not df.empty:
        df["pub_date"] = pd.to_datetime(df["pub_date"])
    return df


@st.cache_data(ttl=300)
def load_analyses() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT report_url, kind, content_json FROM analyses").fetchall()
    conn.close()
    out = {}
    for row in rows:
        out[(row["report_url"], row["kind"])] = json.loads(row["content_json"])
    return out


def do_refresh():
    with st.spinner("抓取新报告..."):
        n_fetched = fetch_new(limit=None)
    with st.spinner("提取指标..."):
        n_indicators = extract_all()
    with st.spinner("单篇再分析..."):
        n_analyzed = analyze_new_singles()
    month = latest_month()
    if month:
        with st.spinner(f"{month} 综合研判..."):
            analyze_month_cross(month, force=True)
    st.cache_data.clear()
    st.success(
        f"完成：新增 {n_fetched} 篇报告，提取 {n_indicators} 个指标，分析 {n_analyzed} 篇报告。"
    )


st.title("宏观数据解读监控与再分析")

with st.sidebar:
    st.header("数据操作")
    if st.button("刷新抓取 + 再分析", type="primary"):
        do_refresh()
    st.caption("抓取新报告、提取指标、跑单篇与本月综合再分析。可能需要几分钟。")

reports_df = load_reports()
indicators_df = load_indicators()
analyses = load_analyses()

st.header("指标时间序列")
if indicators_df.empty:
    st.info("暂无指标数据，请先在侧边栏刷新。")
else:
    all_names = sorted(indicators_df["name"].unique())
    default_names = [
        n
        for n in all_names
        if "制造业采购经理指数" in n or n in ("CPI同比", "PPI同比")
    ]
    selected = st.multiselect("选择指标", all_names, default=default_names or all_names[:3])
    if selected:
        chart_df = indicators_df[indicators_df["name"].isin(selected)]
        fig = px.line(
            chart_df,
            x="pub_date",
            y="value",
            color="name",
            markers=True,
            labels={"pub_date": "发布日期", "value": "数值", "name": "指标"},
        )
        st.plotly_chart(fig, width="stretch")

st.header("本月综合研判")
month = latest_month()
cross = analyses.get((f"cross:{month}", "cross")) if month else None
if cross is None:
    st.info(f"{month or '（暂无数据）'} 尚无综合研判，请在侧边栏刷新。")
else:
    st.subheader(f"{month} 整体研判")
    st.write(cross["overall_assessment"])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**信号背离**")
        if cross["divergences"]:
            for d in cross["divergences"]:
                st.markdown(f"- {d['description']}")
                st.caption("涉及指标: " + "、".join(d["indicators_involved"]))
        else:
            st.caption("无")
    with col2:
        st.markdown("**信号共振**")
        if cross["convergences"]:
            for c in cross["convergences"]:
                st.markdown(f"- {c}")
        else:
            st.caption("无")

    st.markdown("**拐点识别**")
    if cross["inflection_points"]:
        for p in cross["inflection_points"]:
            st.markdown(f"- **{p['indicator']}**: {p['description']}")
    else:
        st.caption("无")

    st.markdown("**与近 3 个月趋势对比**")
    st.write(cross["trend_vs_recent_3m"])

st.header("报告列表与单篇再分析")
for _, row in reports_df.iterrows():
    single = analyses.get((row["url"], "single"))
    sentiment = single["sentiment"] if single else "未分析"
    with st.expander(
        f"[{row['category']}] {row['title']}  ·  {row['pub_date'][:10]}  ·  {sentiment}"
    ):
        st.markdown(f"[原文链接]({row['url']})")
        if single is None:
            st.caption("尚未分析，请在侧边栏刷新。")
        else:
            st.markdown("**核心结论**")
            for c in single["core_conclusions"]:
                st.markdown(f"- {c}")
            if single["risk_flags"]:
                st.markdown("**风险提示**")
                for r in single["risk_flags"]:
                    st.markdown(f"- {r}")
            if single["industry_highlights"]:
                st.markdown("**行业亮点**")
                for h in single["industry_highlights"]:
                    st.markdown(f"- {h}")
        with st.container():
            st.text(row["raw_text"][:500] + ("..." if len(row["raw_text"]) > 500 else ""))
