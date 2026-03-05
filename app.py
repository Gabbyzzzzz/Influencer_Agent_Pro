import os
import streamlit as st
# config must be imported before agents (injects Streamlit secrets into env vars)
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

st.set_page_config(
    page_title="Influencer Agent Pro",
    layout="wide",
    page_icon="✦",
    initial_sidebar_state="expanded",
)

# ======================== Custom CSS ========================

st.markdown("""
<style>
    /* --- Global --- */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* --- Header area --- */
    .main-header {
        padding: 1.5rem 0 1rem 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        font-size: 1.75rem;
        font-weight: 700;
        color: #1E293B;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .main-header p {
        color: #64748B;
        font-size: 0.9rem;
        margin: 0.25rem 0 0 0;
    }

    /* --- Metric cards --- */
    [data-testid="stMetric"] {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem;
        font-weight: 500;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1E293B;
    }

    /* --- Sidebar --- */
    [data-testid="stSidebar"] {
        background: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    [data-testid="stSidebar"] .stMarkdown h1 {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1E293B;
        letter-spacing: -0.01em;
    }

    /* --- Buttons --- */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        font-size: 0.85rem;
        padding: 0.5rem 1rem;
        transition: all 0.15s ease;
    }
    .stButton > button[kind="primary"] {
        background: #6366F1;
        border: none;
        color: white;
    }
    .stButton > button[kind="primary"]:hover {
        background: #4F46E5;
        box-shadow: 0 2px 8px rgba(99,102,241,0.3);
    }

    /* --- Data editor --- */
    [data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        overflow: hidden;
    }

    /* --- Section dividers --- */
    .section-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: #334155;
        padding: 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .section-title .step-badge {
        background: #6366F1;
        color: white;
        font-size: 0.7rem;
        font-weight: 600;
        padding: 0.15rem 0.5rem;
        border-radius: 4px;
        letter-spacing: 0.03em;
    }

    /* --- Top pick banner --- */
    .top-pick {
        background: linear-gradient(135deg, #F0FDF4, #DCFCE7);
        border: 1px solid #BBF7D0;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin: 0.75rem 0;
    }
    .top-pick strong { color: #166534; }
    .top-pick .label { color: #15803D; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }

    /* --- Toast / status --- */
    [data-testid="stStatusWidget"] {
        border-radius: 12px;
    }

    /* --- Hide default decorations --- */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ======================== API Key Check ========================

_required_keys = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "SEARCH_ENGINE_ID"]
_missing = [k for k in _required_keys if not os.getenv(k)]
if _missing:
    st.error(f"Missing required API keys: {', '.join(_missing)}")
    st.info("Configure them in Streamlit Cloud → Settings → Secrets:\n\n"
            '```\nGEMINI_API_KEY = "your_key"\nGOOGLE_API_KEY = "your_key"\nSEARCH_ENGINE_ID = "your_id"\n```')
    st.stop()

# ======================== Helpers ========================

def format_followers(count, verified):
    if not verified and count == 0:
        return "Unverified"
    return f"{count:,}"

def format_price(price_min, price_max):
    if price_min is None:
        return "Pending"
    if price_min == 0 and price_max == 0:
        return "Needs verification"
    return f"${price_min:,.0f} – ${price_max:,.0f}"

def format_time(dt):
    if not dt:
        return ""
    now = datetime.now()
    diff = now - dt
    if diff.days == 0:
        hours = diff.seconds // 3600
        if hours == 0:
            mins = diff.seconds // 60
            return f"{mins}m ago" if mins > 0 else "Just now"
        return f"{hours}h ago"
    if diff.days == 1:
        return "Yesterday"
    return dt.strftime("%m/%d %H:%M")

async def _run_search_and_score(brand_req, platforms, brand_name, budget_range):
    scout = ScoutAgent(platforms=platforms)
    new_count = await scout.run(brand_req, brand_name=brand_name)
    analyst = AnalystAgent()
    await analyst.run(brand_req, budget_range=budget_range)
    return new_count

# ======================== Sidebar ========================

st.sidebar.markdown("#### ✦ Influencer Agent Pro")
st.sidebar.caption("AI-powered influencer discovery & outreach")
st.sidebar.markdown("---")

brand_name = st.sidebar.text_input("Brand Name", placeholder="e.g. Nike, Glossier, ForeverFurEver")
brand_req = st.sidebar.text_area(
    "Brand Requirements",
    placeholder="Describe your product, target audience, region, content style preferences...",
    height=120
)
brand_website = st.sidebar.text_input("Website (optional)", placeholder="https://...")
budget_range = st.sidebar.slider("Budget Range (USD)", 0, 50000, (1000, 10000), step=500)

platforms = st.sidebar.multiselect("Platforms", SUPPORTED_PLATFORMS, default=DEFAULT_PLATFORMS)

with st.sidebar.expander("Advanced Settings"):
    min_followers = st.number_input("Min Followers", value=0, step=1000)
    min_fit_score = st.slider("Min Fit Score for Emails", 0, 100, FIT_SCORE_THRESHOLD)

st.sidebar.markdown("---")

# Launch search
if st.sidebar.button("Search + Score", type="primary", icon="🔍", use_container_width=True):
    if not brand_req:
        st.sidebar.error("Please enter brand requirements first.")
    elif not platforms:
        st.sidebar.error("Please select at least one platform.")
    else:
        with st.status("Agents working...", expanded=True) as status:
            st.write("Scout Agent is searching across platforms...")
            st.write("Analyst Agent will score candidates automatically...")
            try:
                new_count = asyncio.run(
                    _run_search_and_score(brand_req, platforms, brand_name, budget_range)
                )
                st.write(f"Found {new_count} new candidates — scoring complete.")
            except Exception as e:
                st.error(f"Search/scoring failed: {e}")
            status.update(label="Search + Score complete", state="complete")

# Search history
st.sidebar.markdown("---")
with st.sidebar.expander("Search History", expanded=False):
    with get_db() as db:
        recent_batches = db.query(SearchBatch).order_by(SearchBatch.created_at.desc()).limit(10).all()
        if recent_batches:
            for b in recent_batches:
                bcol1, bcol2 = st.sidebar.columns([4, 1])
                with bcol1:
                    st.caption(
                        f"{format_time(b.created_at)} · {b.platforms} · {b.candidate_count or 0} found"
                    )
                with bcol2:
                    if st.button("×", key=f"del_batch_{b.id}", help="Delete this batch"):
                        db.query(Influencer).filter_by(batch_id=b.id).delete()
                        db.query(SearchBatch).filter_by(id=b.id).delete()
                        db.commit()
                        st.rerun()
        else:
            st.caption("No search history yet")

# ======================== Main Content ========================

# Header
st.markdown("""
<div class="main-header">
    <h1>Influencer Agent Pro</h1>
    <p>Discover, evaluate, and reach out to influencers — powered by AI agents</p>
</div>
""", unsafe_allow_html=True)

with get_db() as db:
    all_inf = db.query(Influencer).order_by(Influencer.fit_score.desc()).all()

    if not all_inf:
        st.markdown("")
        st.info("Configure your brand requirements in the sidebar, then click **Search + Score** to get started.")
        st.stop()

    confirmed_count = sum(1 for i in all_inf if i.is_confirmed)
    draft_count = sum(1 for i in all_inf if i.email_draft)
    scored = [i for i in all_inf if i.fit_score is not None]
    avg_score = sum(i.fit_score for i in scored) / len(scored) if scored else 0

    # ================================================================
    # Metrics
    # ================================================================
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Candidates", len(all_inf))
    col2.metric("Avg Fit Score", f"{avg_score:.0f}")
    col3.metric("Confirmed", confirmed_count)
    col4.metric("Emails Drafted", draft_count)

    # Top pick
    top_pick = all_inf[0]
    if top_pick.fit_score and top_pick.fit_score >= TOP_PICK_THRESHOLD:
        st.markdown(f"""
        <div class="top-pick">
            <span class="label">Top Pick</span><br>
            <strong>{top_pick.name}</strong> &nbsp;·&nbsp; {top_pick.platform} &nbsp;·&nbsp;
            {format_followers(top_pick.follower_count, top_pick.followers_verified)} followers &nbsp;·&nbsp;
            Score: {top_pick.fit_score} &nbsp;—&nbsp;
            <em>{top_pick.fit_reason or ''}</em>
        </div>
        """, unsafe_allow_html=True)

    # ================================================================
    # STEP 1: Select Candidates
    # ================================================================
    st.markdown("---")
    st.markdown('<div class="section-title"><span class="step-badge">STEP 1</span> Select Candidates</div>', unsafe_allow_html=True)

    # Filters
    view_col, plat_col, score_col = st.columns([1, 1, 1])

    with view_col:
        all_batches = db.query(SearchBatch).order_by(SearchBatch.created_at.desc()).all()
        view_options = ["All Candidates"]
        batch_map = {}
        for b in all_batches[:5]:
            label = f"{format_time(b.created_at)} · {b.platforms} ({b.candidate_count or 0})"
            view_options.append(label)
            batch_map[label] = b.id
        view_choice = st.selectbox("View", view_options, label_visibility="collapsed")

    if view_choice == "All Candidates":
        display_list = all_inf
    else:
        batch_id = batch_map.get(view_choice)
        display_list = db.query(Influencer).filter_by(batch_id=batch_id)\
            .order_by(Influencer.fit_score.desc()).all() if batch_id else all_inf

    all_platforms = list(set(i.platform for i in display_list if i.platform))
    with plat_col:
        filter_platforms = st.multiselect(
            "Platform", all_platforms, default=all_platforms, label_visibility="collapsed"
        )
    with score_col:
        score_range = st.slider(
            "Fit Score", 0, 100, (DEFAULT_MIN_SCORE, 100), label_visibility="collapsed"
        )

    # Apply filters
    filtered = [
        i for i in display_list
        if (i.platform in filter_platforms)
        and (i.fit_score is None or score_range[0] <= i.fit_score <= score_range[1])
        and (i.follower_count or 0) >= min_followers
    ]

    # Build table
    data = []
    for inf in filtered:
        data.append({
            "ID": inf.id,
            "Select": inf.is_confirmed or False,
            "Name": inf.name or "",
            "Platform": inf.platform or "",
            "Followers": format_followers(inf.follower_count, inf.followers_verified),
            "Fit Score": inf.fit_score if inf.fit_score else 0,
            "Est. Price": format_price(inf.price_min, inf.price_max),
            "Reason": (inf.fit_reason or "")[:40],
            "URL": inf.url or "",
        })

    if data:
        df = pd.DataFrame(data)
        edited_df = st.data_editor(
            df,
            column_config={
                "Select": st.column_config.CheckboxColumn(""),
                "URL": st.column_config.LinkColumn("Link", display_text="Open"),
                "Fit Score": st.column_config.ProgressColumn(min_value=0, max_value=100),
                "ID": st.column_config.NumberColumn(width="small"),
            },
            disabled=["ID", "Name", "Platform", "Followers", "Fit Score", "Est. Price", "Reason"],
            hide_index=True,
            use_container_width=True,
            key="main_table"
        )

        # Action buttons
        action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
        with action_col1:
            if st.button("Save Selection", icon="💾", use_container_width=True):
                save_count = 0
                for _, row in edited_df.iterrows():
                    target = db.query(Influencer).filter_by(id=row['ID']).first()
                    if target:
                        target.is_confirmed = row['Select']
                        save_count += 1
                db.commit()
                st.toast(f"Saved {save_count} candidates")
                st.rerun()

        confirmed_no_draft = [i for i in all_inf if i.is_confirmed and not i.email_draft]

        with action_col2:
            if st.button(
                f"Generate Emails ({len(confirmed_no_draft)})",
                icon="✍️",
                use_container_width=True,
                disabled=len(confirmed_no_draft) == 0,
                type="primary" if confirmed_no_draft else "secondary",
            ):
                with st.spinner(f"Writing emails for {len(confirmed_no_draft)} candidates..."):
                    try:
                        writer = WriterAgent()
                        asyncio.run(writer.run(
                            brand_req or "Brand partnership",
                            brand_name=brand_name,
                            brand_website=brand_website
                        ))
                        st.rerun()
                    except Exception as e:
                        st.error(f"Email generation failed: {e}")

        with action_col3:
            if confirmed_no_draft:
                st.caption("Save your selection first, then generate emails")
            elif confirmed_count > 0 and draft_count > 0:
                st.caption("Emails are ready — scroll down to preview")
            else:
                st.caption("Select candidates → Save → Generate Emails")
    else:
        st.info("No candidates match the current filters. Try lowering the fit score range.")

    # ================================================================
    # STEP 2: Preview Emails
    # ================================================================
    drafts = [(inf.id, inf.name, inf.platform) for inf in all_inf if inf.email_draft]
    if drafts:
        st.markdown("---")
        st.markdown(f'<div class="section-title"><span class="step-badge">STEP 2</span> Preview Emails ({len(drafts)})</div>', unsafe_allow_html=True)

        selected_name = st.selectbox(
            "Select influencer",
            [f"{name} · {plat} (ID:{id})" for id, name, plat in drafts],
            label_visibility="collapsed"
        )
        selected_id = int(selected_name.split("ID:")[1].rstrip(")"))
        selected_inf = db.query(Influencer).filter_by(id=selected_id).first()

        if selected_inf and selected_inf.email_draft:
            edited_draft = st.text_area(
                "Email content (editable)",
                selected_inf.email_draft,
                height=250,
                key=f"draft_{selected_id}",
                label_visibility="collapsed"
            )

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("Save Draft", icon="💾", key="save_draft"):
                    selected_inf.email_draft = edited_draft
                    db.commit()
                    st.toast("Draft saved")
            with btn_col2:
                if st.button("Regenerate", icon="🔄", key="regen_draft"):
                    try:
                        writer = WriterAgent()
                        async def _regen_single():
                            await writer.write_draft(
                                brand_req or "Brand partnership",
                                selected_inf,
                                brand_name=brand_name,
                                brand_website=brand_website
                            )
                        asyncio.run(_regen_single())
                        db.commit()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Regeneration failed: {e}")

    # ================================================================
    # STEP 3: Export
    # ================================================================
    st.markdown("---")
    st.markdown('<div class="section-title"><span class="step-badge">STEP 3</span> Export</div>', unsafe_allow_html=True)
    st.markdown("")

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
            "Download Candidates CSV",
            csv, "influencers.csv", "text/csv",
            icon="📊",
            use_container_width=True,
        )

    with export_col2:
        confirmed_drafts = [
            f"To: {inf.name}\nPlatform: {inf.platform}\nURL: {inf.url}\n\n{inf.email_draft}\n\n{'='*50}\n"
            for inf in all_inf
            if inf.is_confirmed and inf.email_draft
        ]
        if confirmed_drafts:
            st.download_button(
                f"Download Emails ({len(confirmed_drafts)})",
                "\n".join(confirmed_drafts),
                "email_drafts.txt", "text/plain",
                icon="✉️",
                use_container_width=True,
            )
        else:
            st.button("Download Emails", disabled=True, use_container_width=True,
                       help="Confirm candidates and generate emails first")
