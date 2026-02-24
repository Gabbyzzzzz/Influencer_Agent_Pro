import os
import streamlit as st
# config 必须在 agents 之前导入（注入 Streamlit secrets 到环境变量）
from config import (
    SUPPORTED_PLATFORMS, DEFAULT_PLATFORMS,
    FIT_SCORE_THRESHOLD, TOP_PICK_THRESHOLD, DEFAULT_MIN_SCORE
)
import asyncio
import pandas as pd
from datetime import datetime
from database import get_db, Influencer, SearchBatch
from agents.scout import ScoutAgent
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent

st.set_page_config(page_title="Influencer Agent Pro", layout="wide", page_icon="🐾")

# 检查必要的 API 密钥
_required_keys = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "SEARCH_ENGINE_ID"]
_missing = [k for k in _required_keys if not os.getenv(k)]
if _missing:
    st.error(f"缺少必要的 API 密钥: {', '.join(_missing)}")
    st.info("请在 Streamlit Cloud → Settings → Secrets 中配置，格式：\n\n"
            '```\nGEMINI_API_KEY = "你的密钥"\nGOOGLE_API_KEY = "你的密钥"\nSEARCH_ENGINE_ID = "你的ID"\n```')
    st.stop()

# ======================== 辅助函数 ========================

def format_followers(count, verified):
    if not verified and count == 0:
        return "待验证"
    return f"{count:,}"

def format_price(price_min, price_max):
    if price_min is None:
        return "待计算"
    if price_min == 0 and price_max == 0:
        return "需确认粉丝数"
    return f"${price_min:,.0f}-{price_max:,.0f}"

def format_time(dt):
    if not dt:
        return ""
    now = datetime.now()
    diff = now - dt
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            mins = diff.seconds // 60
            return f"{mins}分钟前" if mins > 0 else "刚刚"
        return f"{hours}小时前"
    if diff.days == 1:
        return "昨天"
    return dt.strftime("%m/%d %H:%M")

async def _run_search_and_score(brand_req, platforms, brand_name, budget_range):
    scout = ScoutAgent(platforms=platforms)
    new_count = await scout.run(brand_req, brand_name=brand_name)
    analyst = AnalystAgent()
    await analyst.run(brand_req, budget_range=budget_range)
    return new_count

# ======================== 侧边栏 ========================
st.sidebar.title("🐾 Agent 控制中心")

brand_name = st.sidebar.text_input("品牌名称", placeholder="例如：Nike, Apple...")
brand_req = st.sidebar.text_area(
    "需求描述",
    placeholder="描述产品、目标地区、目标人群、内容风格偏好...",
    height=120
)
brand_website = st.sidebar.text_input("品牌网站 (可选)", placeholder="https://...")
budget_range = st.sidebar.slider("预算范围 (USD)", 0, 50000, (1000, 10000), step=500)

platforms = st.sidebar.multiselect("搜索平台", SUPPORTED_PLATFORMS, default=DEFAULT_PLATFORMS)

with st.sidebar.expander("⚙️ 高级设置"):
    min_followers = st.number_input("最低粉丝数", value=0, step=1000)
    min_fit_score = st.slider("邮件生成最低契合度", 0, 100, FIT_SCORE_THRESHOLD)

st.sidebar.markdown("---")

# 启动搜索
if st.sidebar.button("🚀 搜索 + 评分", width="stretch"):
    if not brand_req:
        st.sidebar.error("请先输入需求描述！")
    elif not platforms:
        st.sidebar.error("请至少选择一个搜索平台！")
    else:
        with st.status("Agent 协作中...", expanded=True) as status:
            st.write(f"🕵️ Scout 正在搜索 {', '.join(platforms)} 平台...")
            st.write("📊 搜索完成后 Analyst 将自动评分...")
            try:
                new_count = asyncio.run(
                    _run_search_and_score(brand_req, platforms, brand_name, budget_range)
                )
                st.write(f"   ✅ 发现 {new_count} 位新候选人，评分完成")
            except Exception as e:
                st.error(f"搜索/评分失败: {e}")
            status.update(label="✅ 搜索 + 评分完成！", state="complete")

# 搜索历史
st.sidebar.markdown("---")
with st.sidebar.expander("📜 搜索历史", expanded=False):
    with get_db() as db:
        recent_batches = db.query(SearchBatch).order_by(SearchBatch.created_at.desc()).limit(10).all()
        if recent_batches:
            for b in recent_batches:
                bcol1, bcol2 = st.sidebar.columns([4, 1])
                with bcol1:
                    st.caption(
                        f"{format_time(b.created_at)} · {b.platforms} · {b.candidate_count or 0}人"
                    )
                with bcol2:
                    if st.button("🗑️", key=f"del_batch_{b.id}", help="删除该批次"):
                        db.query(Influencer).filter_by(batch_id=b.id).delete()
                        db.query(SearchBatch).filter_by(id=b.id).delete()
                        db.commit()
                        st.rerun()
        else:
            st.caption("暂无搜索记录")

# ======================== 主界面 — 线性流程 ========================
st.title("🤖 网红营销智能体 (Pro)")

with get_db() as db:
    all_inf = db.query(Influencer).order_by(Influencer.fit_score.desc()).all()

    if not all_inf:
        st.info("👈 请在左侧配置品牌需求，然后点击「搜索 + 评分」开始。")
        st.stop()

    confirmed_count = sum(1 for i in all_inf if i.is_confirmed)
    draft_count = sum(1 for i in all_inf if i.email_draft)
    scored = [i for i in all_inf if i.fit_score is not None]
    avg_score = sum(i.fit_score for i in scored) / len(scored) if scored else 0

    # ================================================================
    # STEP 1: 概览
    # ================================================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总候选人", len(all_inf))
    col2.metric("平均契合度", f"{avg_score:.0f}")
    col3.metric("已确认", confirmed_count)
    col4.metric("已生成邮件", draft_count)

    # 最佳推荐
    top_pick = all_inf[0]
    if top_pick.fit_score and top_pick.fit_score >= TOP_PICK_THRESHOLD:
        st.success(
            f"🌟 **最佳推荐: {top_pick.name}** | "
            f"平台: {top_pick.platform} | "
            f"粉丝: {format_followers(top_pick.follower_count, top_pick.followers_verified)} | "
            f"契合度: {top_pick.fit_score} — "
            f"_{top_pick.fit_reason or ''}_"
        )

    # ================================================================
    # STEP 2: 选择候选人
    # ================================================================
    st.markdown("---")
    st.subheader("Step 1 · 选择候选人")

    # 视图切换 + 筛选（紧凑一行）
    view_col, plat_col, score_col = st.columns([1, 1, 1])

    with view_col:
        all_batches = db.query(SearchBatch).order_by(SearchBatch.created_at.desc()).all()
        view_options = ["全部候选人"]
        batch_map = {}
        for b in all_batches[:5]:
            label = f"{format_time(b.created_at)} · {b.platforms} ({b.candidate_count or 0}人)"
            view_options.append(label)
            batch_map[label] = b.id
        view_choice = st.selectbox("查看", view_options, label_visibility="collapsed")

    # 根据视图选择确定显示列表
    if view_choice == "全部候选人":
        display_list = all_inf
    else:
        batch_id = batch_map.get(view_choice)
        display_list = db.query(Influencer).filter_by(batch_id=batch_id)\
            .order_by(Influencer.fit_score.desc()).all() if batch_id else all_inf

    all_platforms = list(set(i.platform for i in display_list if i.platform))
    with plat_col:
        filter_platforms = st.multiselect(
            "平台", all_platforms, default=all_platforms, label_visibility="collapsed"
        )
    with score_col:
        score_range = st.slider(
            "契合度", 0, 100, (DEFAULT_MIN_SCORE, 100), label_visibility="collapsed"
        )

    # 应用筛选
    filtered = [
        i for i in display_list
        if (i.platform in filter_platforms)
        and (i.fit_score is None or score_range[0] <= i.fit_score <= score_range[1])
        and (i.follower_count or 0) >= min_followers
    ]

    # 构建表格
    data = []
    for inf in filtered:
        data.append({
            "ID": inf.id,
            "确认": inf.is_confirmed or False,
            "名称": inf.name or "",
            "平台": inf.platform or "",
            "粉丝数": format_followers(inf.follower_count, inf.followers_verified),
            "契合度": inf.fit_score if inf.fit_score else 0,
            "预测价格": format_price(inf.price_min, inf.price_max),
            "推荐理由": (inf.fit_reason or "")[:40],
            "链接": inf.url or "",
        })

    if data:
        df = pd.DataFrame(data)
        edited_df = st.data_editor(
            df,
            column_config={
                "确认": st.column_config.CheckboxColumn("✅"),
                "链接": st.column_config.LinkColumn("打开"),
                "契合度": st.column_config.ProgressColumn(min_value=0, max_value=100),
                "ID": st.column_config.NumberColumn(width="small"),
            },
            disabled=["ID", "名称", "平台", "粉丝数", "契合度", "预测价格", "推荐理由"],
            hide_index=True,
            width="stretch",
            key="main_table"
        )

        # 保存 + 下一步 在同一行
        action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
        with action_col1:
            if st.button("💾 保存选择", width="stretch"):
                save_count = 0
                for _, row in edited_df.iterrows():
                    target = db.query(Influencer).filter_by(id=row['ID']).first()
                    if target:
                        target.is_confirmed = row['确认']
                        save_count += 1
                db.commit()
                st.toast(f"已保存 {save_count} 条！")
                st.rerun()

        # 计算待生成邮件的确认候选人
        confirmed_no_draft = [i for i in all_inf if i.is_confirmed and not i.email_draft]

        with action_col2:
            if st.button(
                f"✍️ 生成邮件 ({len(confirmed_no_draft)})",
                width="stretch",
                disabled=len(confirmed_no_draft) == 0,
                type="primary" if confirmed_no_draft else "secondary",
            ):
                with st.spinner(f"正在为 {len(confirmed_no_draft)} 位候选人生成邮件..."):
                    try:
                        writer = WriterAgent()
                        asyncio.run(writer.run(
                            brand_req or "品牌合作",
                            brand_name=brand_name,
                            brand_website=brand_website
                        ))
                        st.rerun()
                    except Exception as e:
                        st.error(f"邮件生成失败: {e}")

        with action_col3:
            if confirmed_no_draft:
                st.caption(f"⬆️ 先「保存选择」，再点「生成邮件」")
            elif confirmed_count > 0 and draft_count > 0:
                st.caption("✅ 邮件已就绪，请往下查看")
            else:
                st.caption("勾选候选人 → 保存 → 生成邮件")
    else:
        st.info("没有符合筛选条件的候选人。试试降低契合度范围。")

    # ================================================================
    # STEP 3: 预览邮件
    # ================================================================
    drafts = [(inf.id, inf.name, inf.platform) for inf in all_inf if inf.email_draft]
    if drafts:
        st.markdown("---")
        st.subheader(f"Step 2 · 预览邮件 ({len(drafts)})")

        selected_name = st.selectbox(
            "选择博主",
            [f"{name} · {plat} (ID:{id})" for id, name, plat in drafts],
            label_visibility="collapsed"
        )
        selected_id = int(selected_name.split("ID:")[1].rstrip(")"))
        selected_inf = db.query(Influencer).filter_by(id=selected_id).first()

        if selected_inf and selected_inf.email_draft:
            edited_draft = st.text_area(
                "邮件内容（可编辑）",
                selected_inf.email_draft,
                height=250,
                key=f"draft_{selected_id}",
                label_visibility="collapsed"
            )

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("💾 保存修改", key="save_draft"):
                    selected_inf.email_draft = edited_draft
                    db.commit()
                    st.toast("邮件已保存！")
            with btn_col2:
                if st.button("🔄 重新生成", key="regen_draft"):
                    try:
                        writer = WriterAgent()
                        async def _regen_single():
                            await writer.write_draft(
                                brand_req or "品牌合作",
                                selected_inf,
                                brand_name=brand_name,
                                brand_website=brand_website
                            )
                        asyncio.run(_regen_single())
                        db.commit()
                        st.rerun()
                    except Exception as e:
                        st.error(f"重新生成失败: {e}")

    # ================================================================
    # STEP 4: 导出
    # ================================================================
    st.markdown("---")
    st.subheader("Step 3 · 导出")
    export_col1, export_col2 = st.columns(2)

    with export_col1:
        export_data = []
        for inf in all_inf:
            export_data.append({
                "Name": inf.name,
                "Platform": inf.platform,
                "Handle": inf.platform_handle,
                "Followers": inf.follower_count if inf.followers_verified else "Unverified",
                "Fit Score": inf.fit_score,
                "Fit Reason": inf.fit_reason,
                "Price Range": format_price(inf.price_min, inf.price_max),
                "URL": inf.url,
                "Confirmed": inf.is_confirmed,
            })
        csv = pd.DataFrame(export_data).to_csv(index=False)
        st.download_button(
            "📊 导出候选人 CSV",
            csv, "influencers.csv", "text/csv",
            width="stretch",
        )

    with export_col2:
        confirmed_drafts = [
            f"To: {inf.name}\nPlatform: {inf.platform}\nURL: {inf.url}\n\n{inf.email_draft}\n\n{'='*50}\n"
            for inf in all_inf
            if inf.is_confirmed and inf.email_draft
        ]
        if confirmed_drafts:
            st.download_button(
                f"✉️ 导出已确认邮件 ({len(confirmed_drafts)})",
                "\n".join(confirmed_drafts),
                "email_drafts.txt", "text/plain",
                width="stretch",
            )
        else:
            st.button("✉️ 导出已确认邮件", disabled=True, width="stretch",
                       help="请先确认候选人并生成邮件")
