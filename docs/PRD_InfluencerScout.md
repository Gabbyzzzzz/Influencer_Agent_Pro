# Product Requirements Document (PRD)

# InfluencerScout — AI-Powered Influencer Partnership Platform

---

| Field | Detail |
|-------|--------|
| **Product Name** | InfluencerScout |
| **Version** | 2.0 |
| **Author** | Jiabei Zhang |
| **Date** | 2026-02-24 |
| **Status** | Live (Deployed on Streamlit Cloud) |
| **Live URL** | https://gabbyzzzzz-influencer-agent-pro-app-f5eohp.streamlit.app/ |
| **Repository** | https://github.com/Gabbyzzzzz/Influencer_Agent_Pro |

---

## Table of Contents

1. [Project Background](#1-project-background)
2. [Problem Statement](#2-problem-statement)
3. [Target Users](#3-target-users)
4. [Product Goals & Success Metrics](#4-product-goals--success-metrics)
5. [Solution Overview](#5-solution-overview)
6. [System Architecture](#6-system-architecture)
7. [Tech Stack](#7-tech-stack)
8. [Core Feature Specifications](#8-core-feature-specifications)
9. [User Flow](#9-user-flow)
10. [Data Model](#10-data-model)
11. [API Integrations](#11-api-integrations)
12. [Pricing Model](#12-pricing-model)
13. [UI Specifications](#13-ui-specifications)
14. [Non-Functional Requirements](#14-non-functional-requirements)
15. [Current Status & Milestones](#15-current-status--milestones)
16. [Future Roadmap](#16-future-roadmap)
17. [Risks & Mitigations](#17-risks--mitigations)
18. [Appendix](#18-appendix)

---

## 1. Project Background

Influencer marketing has become a core channel for brand growth, with the global market valued at over $21 billion. However, the process of finding the right influencer partners remains largely manual: brands and marketing teams spend hours scrolling through social platforms, building spreadsheets, guessing pricing, and drafting outreach messages one by one.

InfluencerScout was built to automate this entire workflow. It is an AI-powered multi-agent system that discovers relevant influencers across YouTube, Instagram, and TikTok, scores them for brand fit, estimates collaboration pricing, and generates personalized outreach emails — all in a single, streamlined interface.

The system is designed for brands, agencies, and marketing teams who need to move fast and scale their influencer partnerships without sacrificing quality or personalization.

---

## 2. Problem Statement

### Current Pain Points

| Problem | Impact |
|---------|--------|
| **Manual discovery is slow** | Finding relevant creators across 3+ platforms takes hours per campaign |
| **No standardized evaluation** | Fit assessment is subjective — different team members score differently |
| **Pricing is opaque** | Brands rely on anecdotal data or expensive third-party tools for pricing |
| **Follower counts are unreliable** | Public-facing numbers can be outdated or inflated; no verification |
| **Outreach is generic** | Mass-produced templates lead to low response rates |
| **No single source of truth** | Candidate data is scattered across spreadsheets, browser tabs, and email threads |

### How This Product Solves Them

| Problem | Solution |
|---------|----------|
| Manual discovery | AI-generated search queries tailored per platform, 50+ results per search batch |
| Subjective evaluation | Standardized 1-100 fit score with auditable reasoning from AI |
| Opaque pricing | Tiered pricing model based on verified follower count, platform, and engagement |
| Unreliable follower counts | Real-time verification via YouTube Data API; framework ready for Instagram/TikTok APIs |
| Generic outreach | Personalized emails referencing specific influencer content and brand value proposition |
| Scattered data | Persistent SQLite database with full audit trail per candidate |

---

## 3. Target Users

### Primary

- **Brand Marketing Teams** — In-house marketers managing influencer partnerships for product launches, campaigns, or ongoing brand awareness
- **Marketing Agencies** — Teams running influencer campaigns for multiple clients who need to scale discovery and outreach

### Secondary

- **Startup Founders** — Early-stage companies exploring influencer marketing without dedicated marketing headcount
- **E-commerce Brands** — DTC brands seeking cost-effective creator partnerships to drive sales

### User Persona

> **Sarah, Brand Partnership Manager**
>
> Sarah manages influencer partnerships for a pet product brand. She currently spends 3-4 hours per campaign manually searching YouTube and Instagram, building spreadsheets, and drafting outreach emails. She needs a tool that can find relevant creators fast, give her a clear picture of who fits and what they cost, and help her write emails that actually get responses.

---

## 4. Product Goals & Success Metrics

### Goals

1. Reduce influencer discovery time from hours to minutes
2. Provide data-driven, standardized candidate evaluation
3. Generate high-quality, personalized outreach at scale
4. Centralize all candidate data in a queryable, exportable format

### Key Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| **Time to First Candidate** | Time from brand requirement input to first scored result | < 3 minutes |
| **Discovery Throughput** | Unique candidates discovered per search batch | 30-50 per batch |
| **Score Accuracy** | Proportion of top-5 candidates that a human reviewer would also shortlist | > 70% |
| **Email Quality** | Proportion of generated drafts used as-is or with minor edits | > 60% |
| **Platform Coverage** | Candidates discovered across all selected platforms | 3 platforms supported |

---

## 5. Solution Overview

InfluencerScout uses a **Multi-Agent Architecture** where three specialized AI agents collaborate asynchronously:

```
Brand Requirement (user input)
        │
        ▼
   ┌─────────┐     Google Custom Search API
   │  Scout   │────→ YouTube Data API v3
   │  Agent   │     Instagram / TikTok APIs
   └────┬─────┘
        │  Discovered candidates stored in DB
        ▼
   ┌──────────┐
   │ Analyst  │────→ Gemini 2.0 Flash
   │  Agent   │     (fit scoring + pricing)
   └────┬─────┘
        │  Scored candidates updated in DB
        ▼
   ┌──────────┐
   │  Writer  │────→ Gemini 2.0 Flash
   │  Agent   │     (personalized email generation)
   └────┬─────┘
        │
        ▼
   User Review & Export (Streamlit UI)
```

Each agent operates independently with its own prompts, validation logic, and error handling. Agents communicate through the shared SQLite database, enabling a clean separation of concerns.

---

## 6. System Architecture

### Architecture Pattern

**Layered Agent Architecture with Shared Memory**

```
┌─────────────────────────────────────────────┐
│                  UI Layer                    │
│            Streamlit (app.py)                │
│   Input → Status → Table → Email → Export   │
├─────────────────────────────────────────────┤
│               Agent Layer                    │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐     │
│  │  Scout  │ │ Analyst  │ │  Writer  │     │
│  └────┬────┘ └────┬─────┘ └────┬─────┘     │
│       │           │            │            │
├───────┴───────────┴────────────┴────────────┤
│             Platform Layer                   │
│  ┌──────────┐ ┌───────────┐ ┌────────┐     │
│  │ YouTube  │ │ Instagram │ │ TikTok │     │
│  │ Provider │ │ Provider  │ │Provider│     │
│  └──────────┘ └───────────┘ └────────┘     │
├─────────────────────────────────────────────┤
│              Data Layer                      │
│       SQLAlchemy + SQLite                    │
│    (Influencer, SearchBatch tables)          │
└─────────────────────────────────────────────┘
```

### Design Principles

1. **Pluggable Platform Providers** — Abstract base class (`PlatformProvider`) enables adding new platforms by implementing 5 methods
2. **Lazy Initialization** — API clients are created on first use, not at import time (critical for cloud deployment)
3. **Concurrency Control** — `asyncio.Semaphore` limits parallel API calls to prevent rate limiting
4. **Graceful Degradation** — Missing optional API keys (Instagram, TikTok) don't block discovery; candidates are still found via Google Search
5. **Shared Memory via DB** — Agents don't communicate directly; they read/write to the same database, enabling independent execution and retry

---

## 7. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **AI Model** | Google Gemini 2.0 Flash | Query generation, fit scoring, pricing, email drafting |
| **Search** | Google Custom Search API | Cross-platform influencer discovery |
| **Data Enrichment** | YouTube Data API v3 | Verified subscriber counts |
| **Data Enrichment** | Instagram Graph API | Follower counts (optional) |
| **Data Enrichment** | TikTok Research API | Follower counts + engagement (optional) |
| **Backend** | Python 3.10+, asyncio | Async agent orchestration |
| **ORM** | SQLAlchemy 2.0 | Database abstraction |
| **Database** | SQLite | Persistent storage (lightweight, zero-config) |
| **Frontend** | Streamlit | Interactive web UI |
| **Deployment** | Streamlit Cloud | Managed hosting with secrets management |
| **Dev Environment** | GitHub Codespaces (devcontainer) | One-click development setup |

### Dependencies

```
streamlit>=1.40.0
google-genai>=1.0.0
google-api-python-client>=2.100.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
```

**Total codebase**: ~1,400 lines of Python across 11 source files.

---

## 8. Core Feature Specifications

### F1: Multi-Platform Influencer Discovery

**Owner**: Scout Agent (`agents/scout.py`)

**Description**: Automatically discovers relevant influencer profiles across YouTube, Instagram, and TikTok using AI-generated search queries.

**Behavior**:
1. User provides brand requirement text and selects platforms
2. Gemini generates 5 diverse search queries per platform, each targeting a different angle:
   - Product category keywords
   - Creator type keywords
   - Audience demographics
   - Content style keywords
   - Niche community terms
3. Each query is executed via Google Custom Search (10 results per query)
4. Results are filtered through a URL blacklist (non-profile pages removed)
5. Results are deduplicated against existing database records
6. For each valid URL, the platform provider fetches real follower data
7. All candidates are saved to the database with a batch_id for tracking

**Configuration**:

| Parameter | Value | Description |
|-----------|-------|-------------|
| QUERIES_PER_PLATFORM | 5 | Search queries generated per platform |
| SEARCH_RESULTS_PER_QUERY | 10 | Google results per query |
| MAX_CONCURRENT_API | 5 | Parallel API call limit |

**Typical yield**: 30-50 unique candidates per search batch (across selected platforms).

---

### F2: AI-Powered Fit Scoring & Pricing

**Owner**: Analyst Agent (`agents/analyst.py`)

**Description**: Evaluates each candidate's brand fit and estimates collaboration pricing using a tiered model.

**Behavior**:
1. Unscored candidates are grouped into batches of 5
2. Each batch is sent to Gemini with the brand requirement, candidate details, and pricing guidelines
3. Gemini returns a JSON array with `fit_score`, `fit_reason`, `price_min`, `price_max` per candidate
4. Response is parsed through a 3-layer fallback: direct JSON → markdown code block extraction → regex
5. Scores are validated (clamped to 1-100, prices corrected if inverted)
6. Results are written to the database

**Fit Score (1-100)**:
- Considers: content vertical alignment, audience relevance, follower count, platform suitability
- Includes a short Chinese-language reasoning (≤50 characters)

**Pricing Model**: See [Section 12](#12-pricing-model) for full detail.

---

### F3: Personalized Outreach Email Generation

**Owner**: Writer Agent (`agents/writer.py`)

**Description**: Generates personalized English outreach emails for user-confirmed candidates.

**Behavior**:
1. Only generates emails for candidates where `is_confirmed = True` and `email_draft = None`
2. Each email prompt includes brand name, website, product description, and the Analyst's fit reasoning
3. Generated email follows a 5-section structure:
   - **Subject Line** — Attention-grabbing, specific to the influencer
   - **Opening** — References the influencer's specific content (not generic)
   - **Value Proposition** — What the brand offers and why this influencer specifically
   - **CTA** — Clear next step (e.g., schedule a call)
   - **Sign Off** — Professional but warm
4. Word count is validated: target 120 words, truncated at 180 words

**Anti-patterns avoided**:
- No "I hope this email finds you well"
- No vague flattery — must reference specific content
- No corporate jargon

---

### F4: Candidate Management & Export

**Owner**: UI (`app.py`)

**Description**: Interactive table for reviewing, selecting, and exporting candidates.

**Capabilities**:
- Sortable table with fit score progress bars and clickable profile links
- Checkbox selection for confirming candidates
- Filter by platform, fit score range, and minimum follower count
- View by search batch or all candidates combined
- CSV export of all candidates (name, platform, followers, score, pricing, URL)
- Text export of confirmed outreach emails

---

### F5: Search History & Batch Management

**Owner**: UI (`app.py`) + Database (`database.py`)

**Description**: Every search creates a timestamped batch record, enabling users to compare results across runs.

**Capabilities**:
- View last 10 search batches with platform, candidate count, and relative timestamp
- Filter main table by specific batch
- Delete individual batches and their associated candidates
- Each batch records: brand_requirement, brand_name, platforms, candidate_count, created_at

---

## 9. User Flow

### Primary Workflow

```
Step 1: Configure Search
  ├── Enter brand name
  ├── Describe product/service and target audience
  ├── (Optional) Add brand website
  ├── Set budget range ($0-$50,000)
  ├── Select platforms: YouTube / Instagram / TikTok
  └── Click "Search + Score"

Step 2: Review & Select
  ├── View stats: total candidates, avg fit score, confirmed count
  ├── (Optional) Filter by platform, score range, follower count
  ├── (Optional) Switch view to specific batch
  ├── Check candidates to confirm
  ├── Click "Save"
  └── Click "Generate Emails" for confirmed candidates

Step 3: Refine Outreach
  ├── Select an influencer from dropdown
  ├── Review generated email
  ├── (Optional) Edit email text
  ├── (Optional) Click "Regenerate" for new draft
  └── Click "Save Draft"

Step 4: Export
  ├── Download CSV of all candidates
  └── Download TXT of confirmed outreach emails
```

### System Execution Flow (Backend)

```
User clicks "Search + Score"
  │
  ├── Scout Agent
  │   ├── [Parallel] Generate 5 queries × N platforms via Gemini
  │   ├── [Parallel] Execute all queries via Google Custom Search
  │   ├── Deduplicate + blacklist filter
  │   ├── [Parallel] Fetch follower stats per URL via platform APIs
  │   └── Batch insert to DB
  │
  └── Analyst Agent
      ├── Query DB for unscored candidates
      ├── Group into batches of 5
      ├── [Parallel] Score each batch via Gemini
      ├── Validate + parse JSON responses
      └── Update DB with scores and pricing

User clicks "Generate Emails"
  │
  └── Writer Agent
      ├── Query DB for confirmed + no-draft candidates
      ├── [Parallel] Generate email per candidate via Gemini
      ├── Validate word count
      └── Update DB with email drafts
```

---

## 10. Data Model

### Entity Relationship

```
SearchBatch (1) ──── (N) Influencer
```

### Table: SearchBatch

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | Integer | PK, auto-increment | Batch identifier |
| brand_requirement | Text | | User's product/service description |
| brand_name | String | | Brand name |
| platforms | String | | Comma-separated list (e.g., "YouTube,Instagram") |
| candidate_count | Integer | default=0 | Candidates discovered in this batch |
| created_at | DateTime | default=now | Batch creation timestamp |

### Table: Influencer

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| **Identity** | | | |
| id | Integer | PK, auto-increment | Candidate identifier |
| batch_id | Integer | FK → SearchBatch.id | Which search batch found this candidate |
| name | String | | Display name |
| platform | String | indexed | YouTube / Instagram / TikTok |
| platform_handle | String | | @username |
| url | String | UNIQUE | Profile URL (dedup key) |
| **Metrics** | | | |
| follower_count | Integer | default=0 | Subscriber/follower count |
| followers_verified | Boolean | default=False | True if count came from platform API |
| engagement_rate | Float | | Platform-specific engagement metric |
| tags | String | | Google Search snippet |
| niche | String | | Content category |
| language | String | | Primary content language |
| **Scoring** | | | |
| fit_score | Integer | indexed | Brand fit score (1-100) |
| fit_reason | Text | | AI-generated reasoning |
| price_min | Float | | Estimated min collaboration price (USD) |
| price_max | Float | | Estimated max collaboration price (USD) |
| **Outreach** | | | |
| email_draft | Text | | Generated outreach email |
| is_confirmed | Boolean | indexed, default=False | User selected this candidate |
| **Tracking** | | | |
| error_count | Integer | default=0 | Failed API attempts |
| created_at | DateTime | default=now | Discovery timestamp |
| updated_at | DateTime | auto-update | Last modification |

### Indexes

- `ix_platform` — Fast platform-based filtering
- `ix_fit_score` — Fast score-based sorting
- `ix_is_confirmed` — Fast confirmed-only queries
- `ix_batch_id` — Fast batch-based filtering

---

## 11. API Integrations

### Required APIs

| API | Provider | Purpose | Auth Method |
|-----|----------|---------|-------------|
| **Gemini 2.0 Flash** | Google AI Studio | AI reasoning (query gen, scoring, emails) | API Key (`GEMINI_API_KEY`) |
| **Google Custom Search** | Google Cloud | Cross-platform influencer discovery | API Key (`GOOGLE_API_KEY`) + Engine ID (`SEARCH_ENGINE_ID`) |
| **YouTube Data API v3** | Google Cloud | Verified subscriber counts | API Key (`GOOGLE_API_KEY`) |

### Optional APIs

| API | Provider | Purpose | Auth Method |
|-----|----------|---------|-------------|
| **Instagram Graph API** | Meta | Follower counts for Instagram creators | Access Token (`INSTAGRAM_ACCESS_TOKEN`) + User ID (`INSTAGRAM_USER_ID`) |
| **TikTok Research API** | TikTok | Follower counts + engagement data | Client Credentials (`TIKTOK_CLIENT_KEY` + `TIKTOK_CLIENT_SECRET`) |

### Graceful Degradation

When optional APIs are not configured:
- Candidates are still **discovered** via Google Custom Search
- Follower counts display as "To be verified" (0 with `followers_verified=False`)
- Pricing shows as "Requires follower confirmation" ($0-$0)
- The system explicitly marks these candidates for manual follow-up

---

## 12. Pricing Model

The Analyst Agent estimates collaboration pricing using a tiered model:

### Tier Definitions

| Tier | Follower Range | Price Formula (USD) |
|------|---------------|-------------------|
| **Nano** | < 10K | Fixed range: $50 - $200 |
| **Micro** | 10K - 100K | followers × $0.02 to followers × $0.05 |
| **Mid** | 100K - 500K | followers × $0.05 to followers × $0.08 |
| **Macro** | 500K+ | followers × $0.08 to followers × $0.12 |

### Platform Coefficients

| Platform | Coefficient | Rationale |
|----------|------------|-----------|
| YouTube (long-form) | ×1.0 | Baseline; highest CPM |
| Instagram (posts/Reels) | ×0.6 | Lower reach per unit |
| TikTok (short-form) | ×0.4 - 0.8 | Base ×0.4; high engagement can push to ×0.8 |

### Premium Factors

| Factor | Modifier | When Applied |
|--------|----------|-------------|
| Niche specialist | +20-50% | Creator's vertical tightly aligns with brand |
| High engagement rate | +10-30% | Above-average likes/comments ratio |

### Special Cases

| Condition | Price Output | Meaning |
|-----------|-------------|---------|
| Followers = 0, unverified | $0 - $0 | Needs follower verification before pricing |
| Verified followers > 0 | Calculated per tier | Standard pricing applied |

### Example Calculations

| Creator | Followers | Platform | Tier | Base Price | Coefficient | Final Range |
|---------|-----------|----------|------|-----------|-------------|-------------|
| Pet Vlogger A | 850K | YouTube | Macro | $68K-$102K | ×1.0 | **$68,000-$102,000** |
| Fashion Creator B | 45K | Instagram | Micro | $900-$2,250 | ×0.6 | **$540-$1,350** |
| Dance Creator C | 200K | TikTok | Mid | $10K-$16K | ×0.4 | **$4,000-$6,400** |
| Niche Expert D | 8K | YouTube | Nano | $50-$200 | ×1.0 | **$50-$200** |

---

## 13. UI Specifications

### Layout

- **Page layout**: Wide mode (sidebar + main content area)
- **Theme**: Custom (#FF6B6B primary accent, white background, light gray secondary)
- **Icon**: 🐾

### Sidebar Components

| Component | Type | Details |
|-----------|------|---------|
| Brand name | Text input | Placeholder: "e.g., Nike, Apple..." |
| Requirement description | Text area | 120px height, guidance on product/region/audience |
| Brand website | Text input | Optional, prefix "https://..." |
| Budget range | Slider | $0-$50,000, step $500, default $1,000-$10,000 |
| Platform selector | Multiselect | YouTube, Instagram, TikTok; default: YouTube |
| Advanced settings | Expander | Min followers (0), min fit score for emails (60) |
| Search + Score button | Button | Full width, triggers Scout + Analyst |
| Search history | Expander | Last 10 batches with delete buttons |

### Main Content Components

| Section | Components |
|---------|-----------|
| **Metrics bar** | 4 cards: Total candidates, Avg fit score, Confirmed count, Email count |
| **Top pick banner** | Green alert for score ≥ 80 with name, platform, followers, reason |
| **Filter bar** | Batch selector dropdown, platform multiselect, score range slider |
| **Data table** | Editable data_editor with checkboxes, progress bars, links |
| **Action buttons** | Save selection, Generate emails (with count), contextual help text |
| **Email preview** | Dropdown selector, editable text area, save/regenerate buttons |
| **Export** | CSV download (all candidates), TXT download (confirmed emails) |

### API Key Validation

On startup, the app checks for 3 required environment variables. If any are missing, a clear error message is displayed with setup instructions, and the app halts.

---

## 14. Non-Functional Requirements

### Performance

| Metric | Requirement |
|--------|------------|
| End-to-end search + score | < 3 minutes for single platform |
| Concurrent API calls | Max 5 parallel (semaphore-controlled) |
| Database queries | < 100ms for typical table loads |
| UI responsiveness | No blocking during agent execution (async) |

### Scalability

| Aspect | Current | Path to Scale |
|--------|---------|--------------|
| Database | SQLite (single file) | Migrate to PostgreSQL for concurrent writes |
| Users | Single-user (no auth) | Add authentication layer |
| Candidates | Hundreds per session | Pagination for 10K+ records |
| Platforms | 3 (YouTube, Instagram, TikTok) | Add via PlatformProvider interface |

### Security

| Concern | Mitigation |
|---------|-----------|
| API key exposure | Keys stored in environment variables / Streamlit secrets; never committed to git |
| SQL injection | SQLAlchemy ORM with parameterized queries |
| Data privacy | No PII stored beyond public profile information |
| Input validation | Score clamping, URL deduplication, word count limits |

### Reliability

| Concern | Mitigation |
|---------|-----------|
| API failures | Try/except per call; individual failures don't block batch |
| JSON parse failures | 3-layer fallback: direct parse → code block extraction → regex |
| Rate limiting | Semaphore limits concurrent calls; lazy client initialization |
| Cloud filesystem | Logger degrades gracefully if file writes fail |

### Deployment

| Aspect | Detail |
|--------|--------|
| Platform | Streamlit Cloud (managed) |
| CI/CD | Auto-deploy on push to main branch |
| Secrets | Streamlit Cloud Secrets (TOML format) |
| Python version | 3.10+ (cloud default) |
| Dev environment | GitHub Codespaces via devcontainer |

---

## 15. Current Status & Milestones

### Completed (v2.0 — Current Release)

| Milestone | Description | Status |
|-----------|-------------|--------|
| **M1: Core Pipeline** | Scout → Analyst → Writer pipeline with YouTube support | Done |
| **M2: Database & Persistence** | SQLAlchemy ORM, context-managed sessions, search batches | Done |
| **M3: Multi-Platform Architecture** | PlatformProvider abstraction + YouTube/Instagram/TikTok providers | Done |
| **M4: Scoring & Pricing** | Tiered pricing model, platform coefficients, JSON validation | Done |
| **M5: UI Overhaul** | Linear workflow, filters, batch management, email editing, export | Done |
| **M6: Quality & Stability** | Logging system, error handling, lazy initialization, input validation | Done |
| **M7: Deployment** | Streamlit Cloud deployment, secrets management, requirements optimization | Done |

### What's Working Today

- Full search pipeline across YouTube, Instagram, and TikTok
- YouTube follower counts verified via API in real-time
- AI-powered fit scoring with tiered pricing estimates
- Personalized outreach email generation for confirmed candidates
- Interactive candidate management with filters and batch views
- CSV and email export
- Deployed and accessible via public URL

---

## 16. Future Roadmap

### Phase 1: Data Enrichment (Short-term)

| Feature | Description | Priority |
|---------|-------------|----------|
| Instagram Graph API enrollment | Complete Meta developer setup to enable verified Instagram follower counts | High |
| TikTok Research API enrollment | Complete TikTok developer approval for verified follower + engagement data | High |
| Engagement-based pricing | Incorporate engagement rate into pricing formula (not just follower count) | Medium |
| Scoring history | Track fit_score changes over time to detect trending creators | Medium |

### Phase 2: Workflow Enhancement (Mid-term)

| Feature | Description | Priority |
|---------|-------------|----------|
| Campaign management | Separate candidate pools per product/campaign | High |
| Interaction tracking | Log outreach attempts, responses, and follow-ups per candidate | High |
| Competitor analysis | Input competitor brand name → discover their influencer partners | Medium |
| Bulk email sending | Connect to email service (SendGrid/Mailgun) for direct outreach | Medium |
| User authentication | Multi-user access with role-based permissions | Medium |

### Phase 3: Intelligence & Scale (Long-term)

| Feature | Description | Priority |
|---------|-------------|----------|
| Influencer CRM | Full relationship management: communication history, contract tracking, response rates | High |
| ROI prediction | Predict campaign ROI based on historical performance data | Medium |
| Auto follow-up | Scheduled reminders + AI-generated follow-up emails for non-responders | Medium |
| Chinese platform support | Bilibili, Xiaohongshu (RED), Douyin via browser automation | Low |
| Close-loop analytics | Track email opens, replies, and campaign conversion rates | Medium |
| PostgreSQL migration | Move from SQLite to PostgreSQL for multi-user concurrent access | Medium |

---

## 17. Risks & Mitigations

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **Google API rate limits** | Medium | Search/scoring blocked | Semaphore concurrency control; exponential backoff; quota monitoring |
| **Gemini hallucination** | Medium | Incorrect scores or irrelevant emails | Structured JSON output with validation; human review of fit_reason; regenerate option |
| **API cost overrun** | Low | Unexpected charges | Per-query result limits; batch processing; monitoring usage |
| **SQLite concurrency** | Low | Data corruption with multiple users | Single-user design currently; PostgreSQL migration on roadmap |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| **API deprecation** | Low | Platform access lost | Abstracted provider layer enables quick swap |
| **Pricing model inaccuracy** | Medium | User trust erosion | Clear "estimate" labeling; manual override capability; continuous prompt tuning |
| **Instagram/TikTok API access** | Medium | Incomplete follower data | Graceful degradation; candidates still discoverable; clear "unverified" markers |

---

## 18. Appendix

### A. Environment Variables

| Variable | Required | Source |
|----------|----------|--------|
| `GEMINI_API_KEY` | Yes | [Google AI Studio](https://aistudio.google.com/) |
| `GOOGLE_API_KEY` | Yes | [Google Cloud Console](https://console.cloud.google.com/) |
| `SEARCH_ENGINE_ID` | Yes | [Programmable Search Engine](https://programmablesearchengine.google.com/) |
| `INSTAGRAM_ACCESS_TOKEN` | No | Meta Developer Portal |
| `INSTAGRAM_USER_ID` | No | Meta Graph API Explorer |
| `TIKTOK_CLIENT_KEY` | No | TikTok Developer Portal |
| `TIKTOK_CLIENT_SECRET` | No | TikTok Developer Portal |

### B. Configuration Defaults

| Parameter | Value | File |
|-----------|-------|------|
| BATCH_SIZE | 5 | config.py |
| FIT_SCORE_THRESHOLD | 60 | config.py |
| TOP_PICK_THRESHOLD | 80 | config.py |
| EMAIL_WORD_LIMIT | 120 | config.py |
| MAX_CONCURRENT_API | 5 | config.py |
| SEARCH_RESULTS_PER_QUERY | 10 | config.py |
| QUERIES_PER_PLATFORM | 5 | config.py |
| MAX_RETRIES | 3 | config.py |
| DEFAULT_MIN_SCORE | 40 | config.py |

### C. URL Blacklist Categories

| Category | Examples |
|----------|---------|
| Google services | support.google, policies.google, help.*, docs.* |
| Legal/meta pages | about, terms |
| Platform features | /feed, /discover, /search, /playlist, /shorts, /gaming |
| Non-profile content | /explore, /reels, /stories, /accounts, /music, /tag |
| Instagram non-profile | instagram.com/p/, instagram.com/reel/ |
| TikTok non-profile | tiktok.com/@/video/ |
| File types | .xml, .pdf, robots.txt |

### D. Project File Map

```
InfluencerScout/          (~1,400 LOC)
├── app.py                      # UI orchestration (370 lines)
├── config.py                   # Centralized configuration (47 lines)
├── database.py                 # ORM models + session management (80 lines)
├── agents/
│   ├── __init__.py
│   ├── scout.py                # Discovery agent (237 lines)
│   ├── analyst.py              # Scoring + pricing agent (184 lines)
│   └── writer.py               # Email generation agent (97 lines)
├── utils/
│   ├── __init__.py
│   ├── platform_base.py        # Abstract provider base (32 lines)
│   ├── youtube_utils.py        # YouTube provider (135 lines)
│   ├── instagram_utils.py      # Instagram provider (100 lines)
│   ├── tiktok_utils.py         # TikTok provider (164 lines)
│   └── logger.py               # Logging utility (41 lines)
├── data/
│   └── .gitkeep                # Ensures directory exists in git
├── .streamlit/
│   └── config.toml             # Theme configuration
├── .devcontainer/
│   └── devcontainer.json       # Codespaces environment
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation
└── .gitignore                  # Git exclusions
```

---

*End of PRD*
