import streamlit as st
import asyncio
import pandas as pd
from database import get_db, Influencer
from agents.scout import ScoutAgent
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent

st.set_page_config(page_title="Influencer Agent Pro", layout="wide", page_icon="🐾")

# --- 侧边栏 ---
st.sidebar.title("🐾 Agent 控制中心")
brand_req = st.sidebar.text_area(
    "1. 您的品牌需求描述：",
    placeholder="描述产品、目标地区、人群...",
    height=150
)

# 清空数据库功能
if st.sidebar.button("🗑️ 清空人才库记忆"):
    db = get_db()
    db.query(Influencer).delete()
    db.commit()
    st.sidebar.success("人才库已排空！")
    st.rerun()

# 启动按钮
if st.sidebar.button("🚀 启动全流程搜索", use_container_width=True):
    if not brand_req:
        st.error("请先输入需求内容！")
    else:
        with st.status("Agent 协作中...", expanded=True) as status:
            st.write("🕵️ Scout 正在查询实时 YouTube 粉丝数据...")
            scout = ScoutAgent()
            asyncio.run(scout.run(brand_req))

            st.write("📊 Analyst 正在根据粉丝量计算身价...")
            analyst = AnalystAgent()
            asyncio.run(analyst.run(brand_req))

            st.write("✍️ Writer 正在定制个性化邀约...")
            writer = WriterAgent()
            asyncio.run(writer.run(brand_req))

            status.update(label="✅ 任务全部完成！", state="complete")

# --- 主界面 ---
st.title("🤖 网红营销智能体 (Pro)")

db = get_db()
all_inf = db.query(Influencer).order_by(Influencer.fit_score.desc()).all()

if not all_inf:
    st.info("目前还没有搜寻到博主，请在左侧配置需求并运行。")
else:
    # 3.7 最佳推荐 (Top Pick)
    top_pick = all_inf[0]
    if top_pick.fit_score and top_pick.fit_score >= 80:
        st.success(
            f"🌟 **最佳推荐: {top_pick.name}** | 粉丝数: {top_pick.follower_count:,} | 契合度: {top_pick.fit_score}")
        with st.expander("为什么他是最佳人选？"):
            st.write(top_pick.fit_reason)

    # 3.6 预览表格
    st.subheader("📋 候选人深度分析表")

    data = []
    for inf in all_inf:
        data.append({
            "ID": inf.id,
            "确认": inf.is_confirmed,
            "名称": inf.name,
            "粉丝数": f"{inf.follower_count:,}",
            "契合度": inf.fit_score if inf.fit_score else "待评估",
            "预测价格": f"${inf.price_min}-{inf.price_max}" if inf.price_min else "待计算",
            "链接": inf.url
        })

    df = pd.DataFrame(data)
    edited_df = st.data_editor(
        df,
        column_config={
            "确认": st.column_config.CheckboxColumn(),
            "链接": st.column_config.LinkColumn("打开频道"),
            "契合度": st.column_config.ProgressColumn(min_value=0, max_value=100)
        },
        disabled=["ID", "名称", "粉丝数", "契合度", "预测价格"],
        hide_index=True,
        use_container_width=True,
        key="main_table"
    )

    if st.button("💾 保存选中的博主状态"):
        for index, row in edited_df.iterrows():
            target = db.query(Influencer).filter_by(id=row['ID']).first()
            target.is_confirmed = row['确认']
        db.commit()
        st.toast("确认状态已持久化到数据库")

    # 3.5 邮件草稿预览
    st.markdown("---")
    st.subheader("✉️ 邀约信生成器")
    names_with_drafts = [inf.name for inf in all_inf if inf.email_draft]
    if names_with_drafts:
        selected = st.selectbox("选择博主预览邮件", names_with_drafts)
        selected_inf = db.query(Influencer).filter_by(name=selected).first()
        st.text_area("Email Draft", selected_inf.email_draft, height=250)
    else:
        st.write("评分超过 60 分的博主将自动生成草稿。")