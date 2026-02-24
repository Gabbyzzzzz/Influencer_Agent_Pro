Agent Demo Brief — Influencer Sourcing Agent Pro
=================================================

Purpose
-------
This brief is written for a product manager preparing a live demo of `Influencer Agent Pro`. It covers the background, value proposition, system architecture, data/memory design, demo scripts with expected outcomes, success metrics, known limitations and mitigations, and a short roadmap.

Executive summary
-----------------
- Problem: Sourcing and pricing influencer partnerships is time-consuming and noisy — manual discovery, inconsistent data, and subjective pricing.
- Solution: `Influencer Agent Pro` automates discovery (Scout), scoring/pricing (Analyst), and outreach draft generation (Writer), persisting results in a lightweight memory DB so teams can iterate and act.
- Demo goal: Show how the system discovers real influencer profiles across **YouTube, Instagram, and TikTok**, scores fit and price, and produces ready-to-send outreach drafts — demonstrating speed, repeatability, and traceability.

Background & context
--------------------
- Typical workflow today: search → spreadsheet tracking → manual review → outreach drafts.
- Gaps addressed: inaccurate follower counts (stale data), lack of standardized fit scoring, low throughput for discovery.
- Audience for demo: PMs, growth/partnership leads, and technical stakeholders evaluating feasibility and roadmap.

Value proposition (PM view)
---------------------------
- Faster candidate discovery (minutes vs hours).
- **Multi-platform search**: YouTube, Instagram, TikTok in a single workflow.
- Standardized, auditable `fit_score` and `price` estimates for prioritization.
- Reusable memory DB that records candidates and drafts for downstream ops.
- Clear extension path: historical evaluations, interaction tracking, platform API deep integration.

System overview
---------------
- Agents (async, parallelized):
  - `ScoutAgent`: generates targeted search queries per platform (via Gemini), runs Google Custom Search, enriches YouTube channels with subscriber counts from YouTube Data API, persists `Influencer` records. Supports multi-platform: YouTube (verified subs), Instagram, TikTok (via Google Search discovery).
  - `AnalystAgent`: batches unscored influencers and prompts Gemini to return JSON for `fit_score`, `fit_reason`, and `price_min`/`price_max`. Includes multi-layer JSON parsing with validation.
  - `WriterAgent`: for influencers with `fit_score >= 60`, generates structured English outreach drafts (Subject → Opening → Value Prop → CTA → Sign off) via Gemini.
- Orchestration:
  - UI: `app.py` (Streamlit) runs agents sequentially (Scout → Analyst → Writer) with real-time error reporting and displays ranked results with filters, stats cards, email editing, and CSV/email export.
  - Headless: `test_full_flow.py` runs Scout + Analyst and prints top picks.
- Memory: SQLite (`data/memory.db`) via SQLAlchemy with `Influencer` table (id, name, url, platform, platform_handle, follower_count, engagement_rate, tags, niche, language, fit_score, fit_reason, price_min/max, email_draft, is_confirmed, error_count, created_at, updated_at). Indexed on platform, fit_score, is_confirmed.
- Architecture: Platform Provider abstraction (`PlatformProvider` ABC) enables pluggable platform integrations. Currently implemented: `YouTubeProvider`, `InstagramProvider`, `TikTokProvider`.

Demo prerequisites
------------------
- Environment variables set: `GEMINI_API_KEY`, `GOOGLE_API_KEY`, `SEARCH_ENGINE_ID` in `.env`.
- Python deps installed from `requirements.txt` and network access for Google APIs.
- Optional: populate `data/memory.db` or start fresh (the demo will create records).
- Optional (for enhanced data): `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_USER_ID` for Instagram follower counts; `TIKTOK_CLIENT_KEY` + `TIKTOK_CLIENT_SECRET` for TikTok follower counts.

Demo script (concise, PM-oriented)
----------------------------------
Scenario A — Full UI flow (recommended, 6–10 minutes):
1. Open the app: `streamlit run app.py` and load UI.
2. Enter brand name (e.g., "PetMemorial Co."), requirement ("High-end pet memorial products — target pet-care creators"), and optionally set budget range.
3. **Select platforms**: Choose YouTube + Instagram + TikTok from the multi-select.
4. Click "🚀 启动全流程搜索".
5. Live narrative points while steps run:
   - "Scout searches across all selected platforms in parallel, using AI-generated queries tailored per platform."
   - "For YouTube, it verifies real subscriber counts via YouTube Data API. Instagram and TikTok candidates are discovered via search (API integration for exact follower data is on the roadmap)."
   - "Analyst scores all candidates in batches — returns a numeric `fit_score`, a short `fit_reason`, and platform-aware price estimates."
   - "Writer generates personalized email drafts with the brand name and tailored messaging."
6. Once complete, highlight the stats cards (total candidates, avg score, drafts generated).
7. Show the filter controls: filter by platform, score range, follower count.
8. Open the top pick expander and read `fit_reason`.
9. Open an email draft, demonstrate editing and "重新生成" (regenerate).
10. Show CSV export and email batch export.

Expected outcomes:
- UI shows a ranked, filterable table with candidates from multiple platforms.
- Top pick should have `fit_score >= 80` in a good demo scenario.
- Email drafts include Subject line, personalized opening, and clear CTA.

Scenario B — Headless run for reproducibility (2–4 minutes):
1. Run `python3 test_full_flow.py`.
2. Show terminal output listing top picks and short reasons.
3. Open `data/memory.db` (or the UI) to show persisted rows.

Demo talking points and artifacts to surface
-------------------------------------------
- Show the `Influencer` DB rows (via UI table or DB viewer) to emphasize memory/provenance.
- **Multi-platform discovery**: highlight that the same workflow discovers candidates across YouTube, Instagram, and TikTok.
- Show the platform filter: demonstrate switching between platforms in the UI.
- Explain the uniqueness constraint on `url` and why we verify subscriber counts via YouTube Data API.
- Show an example Gemini prompt used by `AnalystAgent` (in code) to explain deterministic structure (JSON output with few-shot examples).
- Show the export features: CSV for the data team, email batch export for the outreach team.

Success metrics (PM-focused)
---------------------------
- Time-to-first-action: time from brand brief → first reachable top candidate.
- Precision-at-K: proportion of top-K candidates that the PM would shortlist (e.g., K=5).
- Draft acceptance rate: % of generated drafts used as-is or with minor edits.
- Throughput: candidates discovered per hour.
- Platform coverage: % of candidates discovered per platform.

Risks, limitations & mitigations
--------------------------------
- API rate limits & costs (Google APIs, Gemini): include retry/backoff and quota monitoring; show estimated costs for demo scale.
- Model hallucination on scoring or text: mitigate by constraining output (Analyst requests strict JSON with validation), and by surfacing `fit_reason` for human review.
- Data freshness: YouTube subscriber counts are fetched live during discovery, but historic changes require scheduled refresh.
- Instagram/TikTok follower counts: currently require platform-specific API keys (optional). Without them, candidates are still discovered but follower counts show as 0. Platform API integration is on the roadmap.

Roadmap
-------

### Completed (v2.0 — current)
- [x] Multi-platform discovery: YouTube, Instagram, TikTok via Google Custom Search
- [x] Platform Provider architecture (pluggable, extensible)
- [x] YouTube Data API integration for verified subscriber counts
- [x] Structured Prompt engineering with few-shot examples
- [x] Multi-layer JSON parsing with validation
- [x] Brand info pass-through (name, website, budget) for personalized outreach
- [x] Performance optimization: parallel search, cached API services, concurrent stats fetching
- [x] UI overhaul: platform selector, stats cards, filters, email editing, CSV/email export
- [x] Logging system and error handling throughout
- [x] Database schema extension (engagement_rate, niche, language, platform_handle, updated_at)

### Short-term TODO
- [ ] **Integrate Instagram Graph API** for real follower counts (requires Meta developer account + access token; see `.env` comments)
- [ ] **Integrate TikTok Research API** for real follower counts and engagement data (requires TikTok developer approval; see `.env` comments)
- [ ] Add `evaluations` history table for tracking scoring changes over time
- [ ] Add `interactions` table (outreach logs) for tracking sent emails and responses
- [ ] Long-lived token management / auto-refresh for Instagram and TikTok

### Mid-term
- [ ] Chinese platform support: Bilibili, Xiaohongshu (小红书), Douyin (抖音) — using Playwright scraping (already in requirements.txt)
- [ ] Engagement-rate-based pricing model (beyond follower count)
- [ ] Competitor analysis module: discover which influencers competitors work with
- [ ] Campaign management: separate candidate pools per product/campaign

### Long-term
- [ ] Influencer CRM: relationship tracking, communication history, response rates
- [ ] ROI prediction based on historical campaign data
- [ ] Auto-follow-up: scheduled reminders and AI-generated follow-up emails
- [ ] Live outreach integration (connect to email service)
- [ ] Close-loop analytics: track replies and measure campaign ROI

Appendix — Quick run commands & files to show
--------------------------------------------
- Run UI:

```bash
streamlit run app.py
```

- Headless run:

```bash
python3 test_full_flow.py
```

- Files to open during demo:
  - `app.py` — Streamlit orchestration and UI (platform selector, stats, filters, export)
  - `agents/scout.py`, `agents/analyst.py`, `agents/writer.py` — agent logic + prompts
  - `utils/youtube_utils.py` — YouTube Provider with verified subscriber fetch
  - `utils/instagram_utils.py` — Instagram Provider (Google Search + optional Graph API)
  - `utils/tiktok_utils.py` — TikTok Provider (Google Search + optional Research API)
  - `utils/platform_base.py` — Platform abstraction base class
  - `config.py` — centralized configuration
  - `database.py` — `Influencer` schema and `data/memory.db`

Notes & talking scripts
-----------------------
- One-liner pitch: "This agent automates multi-platform influencer sourcing end-to-end — verified discovery across YouTube, Instagram and TikTok, auditable AI scoring, and ready-to-send personalized outreach — so partnership teams can move from hours of manual work to repeatable, measurable workflows."
- Response to "How reliable is the score?": "Scoring is driven by a prompt-engineered Gemini routine that returns structured JSON with few-shot examples and validation; we surface `fit_reason` so humans can audit and override."
- Response to "Why are some follower counts 0?": "YouTube counts are verified live via YouTube Data API. Instagram and TikTok counts require platform-specific API access (Graph API / Research API) — the integration framework is ready, we just need to complete the API enrollment process. Candidates are still discoverable and scorable based on their public profile information."
- Response to "Can this scale?": "The architecture uses async parallelism with semaphore-controlled concurrency, cached API services, and batch processing. Adding new platforms requires implementing a single Provider class."
