# Influencer Agent Pro

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Model](https://img.shields.io/badge/AI-Gemini%202.0%20Flash-orange?logo=google-gemini&logoColor=white)](https://aistudio.google.com/)

An AI-powered multi-agent system that helps brands discover, evaluate, and reach out to the right influencers across YouTube, Instagram, and TikTok.

**[Live Demo](https://gabbyzzzzz-influencer-agent-pro-app-f5eohp.streamlit.app/)**

---

## What It Does

Influencer Agent Pro automates the influencer partnership workflow end-to-end:

1. **Discover** — AI-generated search queries find relevant creators across multiple platforms
2. **Evaluate** — Each candidate is scored on brand fit (1-100) with a price estimate and reasoning
3. **Outreach** — Personalized English outreach emails are generated, ready to send

The entire pipeline runs in minutes instead of hours of manual research.

---

## Architecture

Three specialized AI agents collaborate asynchronously:

```
Brand Requirement
       |
       v
  Scout Agent -----> Google Custom Search + YouTube Data API
       |               (discover candidates, verify follower counts)
       v
 Analyst Agent -----> Gemini 2.0 Flash
       |               (score brand fit, estimate pricing)
       v
  Writer Agent -----> Gemini 2.0 Flash
                       (generate personalized outreach emails)
```

- **Scout Agent** — Generates platform-specific search queries via Gemini, runs them through Google Custom Search, enriches results with real follower counts (YouTube Data API), and deduplicates against existing candidates.
- **Analyst Agent** — Batches candidates and prompts Gemini to score brand fit, predict collaboration pricing (tiered by follower count and platform), and provide reasoning. Multi-layer JSON parsing with validation ensures reliable structured output.
- **Writer Agent** — Generates personalized English outreach emails for confirmed candidates, including subject line, value proposition, and clear CTA.

All agents run with async concurrency control (`asyncio.Semaphore`) for efficient parallel API usage.

---

## Platforms Supported

| Platform | Discovery | Verified Follower Count | Pricing Model |
|----------|-----------|------------------------|---------------|
| YouTube | Google Search + `site:youtube.com/@` | YouTube Data API v3 | Tiered by subscribers + platform coefficient |
| Instagram | Google Search + `site:instagram.com` | Instagram Graph API (optional) | Tiered by followers + platform coefficient |
| TikTok | Google Search + `site:tiktok.com/@` | TikTok Research API (optional) | Tiered by followers + engagement |

---

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/Gabbyzzzzz/Influencer_Agent_Pro.git
cd Influencer_Agent_Pro
pip install -r requirements.txt
```

### 2. Set up API keys

Create a `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_API_KEY=your_google_api_key
SEARCH_ENGINE_ID=your_search_engine_id
```

**Required:**
- `GEMINI_API_KEY` — [Google AI Studio](https://aistudio.google.com/)
- `GOOGLE_API_KEY` — [Google Cloud Console](https://console.cloud.google.com/) (enable Custom Search API + YouTube Data API v3)
- `SEARCH_ENGINE_ID` — [Programmable Search Engine](https://programmablesearchengine.google.com/)

**Optional (for enhanced follower data):**
- `INSTAGRAM_ACCESS_TOKEN` + `INSTAGRAM_USER_ID` — Meta Graph API
- `TIKTOK_CLIENT_KEY` + `TIKTOK_CLIENT_SECRET` — TikTok Research API

### 3. Run

```bash
streamlit run app.py
```

---

## How to Use

1. Enter your brand name and describe your product/service and target audience
2. Select platforms (YouTube, Instagram, TikTok) and set budget range
3. Click **Search + Score** — Scout discovers candidates, Analyst scores them
4. Review the ranked table, check the candidates you want to work with
5. Click **Save**, then **Generate Emails** for confirmed candidates
6. Preview, edit, and export outreach emails

---

## Project Structure

```
Influencer_Agent_Pro/
├── app.py                    # Streamlit UI and workflow orchestration
├── config.py                 # Centralized configuration
├── database.py               # SQLAlchemy models (Influencer, SearchBatch)
├── agents/
│   ├── scout.py              # Discovery agent
│   ├── analyst.py            # Scoring and pricing agent
│   └── writer.py             # Outreach email generation agent
├── utils/
│   ├── platform_base.py      # Abstract base class for platform providers
│   ├── youtube_utils.py      # YouTube provider (verified subscriber counts)
│   ├── instagram_utils.py    # Instagram provider (Graph API integration)
│   ├── tiktok_utils.py       # TikTok provider (Research API integration)
│   └── logger.py             # Logging utility
├── data/
│   └── memory.db             # SQLite database (auto-created)
├── requirements.txt
└── .streamlit/
    └── config.toml           # Streamlit theme configuration
```

---

## Tech Stack

- **AI Model**: Google Gemini 2.0 Flash (scoring, query generation, email drafting)
- **Search**: Google Custom Search API
- **Data Enrichment**: YouTube Data API v3, Instagram Graph API, TikTok Research API
- **Backend**: Python, asyncio, SQLAlchemy + SQLite
- **Frontend**: Streamlit
- **Deployment**: Streamlit Cloud

---

## License

MIT
