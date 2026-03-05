# Influencer Agent Pro — 系统架构与技术栈

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术栈总览](#2-技术栈总览)
- [3. 系统架构图](#3-系统架构图)
- [4. 目录结构](#4-目录结构)
- [5. 核心模块详解](#5-核心模块详解)
  - [5.1 Scout Agent — 发现引擎](#51-scout-agent--发现引擎)
  - [5.2 Analyst Agent — 评分与定价引擎](#52-analyst-agent--评分与定价引擎)
  - [5.3 Writer Agent — 邮件生成引擎](#53-writer-agent--邮件生成引擎)
- [6. 平台数据提供者](#6-平台数据提供者)
- [7. 数据库设计](#7-数据库设计)
- [8. API 集成](#8-api-集成)
- [9. 并发模型与性能](#9-并发模型与性能)
- [10. 配置与部署](#10-配置与部署)
- [11. 安全设计](#11-安全设计)

---

## 1. 项目概述

Influencer Agent Pro 是一个 **AI 驱动的多 Agent 网红营销自动化系统**，覆盖网红发现、品牌契合度评分、合作定价估算、个性化邮件生成的全流程。

**核心能力**：
- 跨平台（YouTube / Instagram / TikTok）网红批量发现
- 基于 LLM 的品牌契合度智能评分（1-100 分）
- 基于粉丝量级和平台的合作报价估算
- 个性化商务合作邮件自动生成
- 候选人筛选、邮件编辑、CSV/TXT 导出

---

## 2. 技术栈总览

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| **AI 模型** | Google Gemini 2.0 Flash | 查询生成、评分推理、邮件撰写 |
| **前端 UI** | Streamlit 1.40+ | 交互式 Web 界面 |
| **后端语言** | Python 3.11+ | 异步编程 (asyncio) |
| **数据库** | SQLite + SQLAlchemy 2.0 | 轻量持久化存储 |
| **搜索引擎** | Google Custom Search API | 跨平台网红发现 |
| **数据验证** | YouTube Data API v3 | 粉丝数实时校验 |
| **数据验证** | Instagram Graph API (可选) | 粉丝数实时校验 |
| **数据验证** | TikTok Research API (可选) | 粉丝数实时校验 |
| **部署平台** | Streamlit Cloud | 无服务器托管 |
| **开发环境** | Dev Container (Python 3.11) | 标准化开发环境 |

**依赖清单** (`requirements.txt`)：

```
streamlit>=1.40.0
google-genai>=1.0.0
google-api-python-client>=2.100.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
pandas>=2.0.0
```

---

## 3. 系统架构图

### 3.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Streamlit Web UI                        │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────┐  │
│  │ 品牌信息输入    │  │ 候选人筛选表格   │  │ 邮件编辑导出  │  │
│  └───────┬────────┘  └────────┬────────┘  └──────┬───────┘  │
└──────────┼─────────────────────┼──────────────────┼──────────┘
           │                     │                  │
           v                     v                  v
┌──────────────────────────────────────────────────────────────┐
│                     Multi-Agent 编排层                        │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Scout Agent  │  │Analyst Agent │  │ Writer Agent │       │
│  │  网红发现     │──▶│ 评分 & 定价   │──▶│  邮件生成    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                  │               │
└─────────┼─────────────────┼──────────────────┼───────────────┘
          │                 │                  │
          v                 v                  v
┌──────────────────────────────────────────────────────────────┐
│                       基础设施层                              │
│                                                              │
│  ┌──────────┐  ┌──────────────────────┐  ┌──────────────┐   │
│  │ SQLite   │  │  External APIs       │  │   Config     │   │
│  │ Database │  │  - Gemini 2.0 Flash  │  │   & Secrets  │   │
│  │          │  │  - Google Search     │  │              │   │
│  │          │  │  - YouTube API       │  │              │   │
│  │          │  │  - Instagram API     │  │              │   │
│  │          │  │  - TikTok API        │  │              │   │
│  └──────────┘  └──────────────────────┘  └──────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 数据流

```
用户输入 (品牌需求, 平台, 预算)
         │
         v
   Scout Agent
   ├── Gemini: 生成搜索关键词 (5条/平台)
   ├── Google Search: 执行搜索 (10结果/查询)
   ├── Platform APIs: 获取粉丝数据
   ├── 去重 & 过滤 (URL 黑名单)
   └── 存入 DB (SearchBatch + Influencer)
         │
         v
   Analyst Agent
   ├── 分批处理 (5人/批)
   ├── Gemini: 品牌契合度评分 (1-100)
   ├── 定价算法: 合作报价估算
   ├── JSON 多层解析 & 校验
   └── 更新 DB (fit_score, price)
         │
         v
   用户筛选 → 勾选候选人
         │
         v
   Writer Agent
   ├── Gemini: 生成个性化邮件
   ├── 字数校验 (≤120词)
   └── 存入 DB (email_draft)
         │
         v
   用户编辑 → 导出 CSV / TXT
```

---

## 4. 目录结构

```
Influencer_Agent_Pro/
├── app.py                      # 主应用入口 (Streamlit UI + 流程编排)
├── config.py                   # 集中配置 (API Keys, 参数常量)
├── database.py                 # 数据库模型 (SQLAlchemy ORM)
├── requirements.txt            # Python 依赖
│
├── agents/                     # AI Agent 模块
│   ├── __init__.py
│   ├── scout.py                # 发现 Agent: 搜索 + 数据采集
│   ├── analyst.py              # 分析 Agent: 评分 + 定价
│   └── writer.py               # 写作 Agent: 邮件生成
│
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── logger.py               # 日志工具
│   ├── platform_base.py        # 平台提供者抽象基类
│   ├── youtube_utils.py        # YouTube 数据提供者
│   ├── instagram_utils.py      # Instagram 数据提供者
│   └── tiktok_utils.py         # TikTok 数据提供者
│
├── data/                       # 运行时数据
│   ├── memory.db               # SQLite 数据库
│   └── agent.log               # 应用日志
│
├── docs/                       # 文档
│   └── PRD_Influencer_Agent_Pro.md
│
├── .streamlit/
│   └── config.toml             # Streamlit 主题 & 服务器配置
│
└── .devcontainer/
    └── devcontainer.json       # Dev Container 开发环境配置
```

**代码规模**：约 1,478 行 Python 代码

---

## 5. 核心模块详解

### 5.1 Scout Agent — 发现引擎

**文件**：`agents/scout.py` (237 行)

**职责**：跨平台网红候选人发现与数据采集

**工作流程**：

```
1. 查询生成 ──────── Gemini 2.0 Flash
   │  输入: 品牌需求 + 平台列表
   │  输出: 5 条搜索指令/平台 (带 site: 前缀)
   v
2. 并行搜索 ──────── Google Custom Search API
   │  每条查询返回 10 个结果
   │  总计: 50-150 个原始候选人
   v
3. URL 过滤 ──────── 黑名单规则
   │  排除: /shorts, /reels, /p/, /explore, /feed 等非主页链接
   │  去重: 数据库唯一约束
   v
4. 数据采集 ──────── Platform APIs (并行)
   │  YouTube: subscriberCount (YouTube Data API v3)
   │  Instagram: followers_count (Graph API, 可选)
   │  TikTok: follower_count (Research API, 可选)
   v
5. 持久化 ──────── SQLite
   创建 SearchBatch + Influencer 记录
```

**关键设计**：
- 搜索查询由 LLM 动态生成，自适应不同品牌需求
- URL 黑名单机制避免爬取非个人主页内容
- 平台 API 不可用时优雅降级（粉丝数返回 0）

---

### 5.2 Analyst Agent — 评分与定价引擎

**文件**：`agents/analyst.py` (184 行)

**职责**：品牌契合度评分 + 合作定价估算

**评分机制**：
- 由 Gemini 2.0 Flash 综合评估粉丝量、内容相关性、互动率
- 输出 1-100 分，附评分理由
- 分批处理（每批 5 人），支持并行

**定价模型**：

| 量级 | 粉丝范围 | 基础报价 |
|------|----------|----------|
| Nano | <10K | $50 - $200 (固定) |
| Micro | 10K - 100K | 粉丝数 × $0.02-$0.05 |
| Mid | 100K - 500K | 粉丝数 × $0.05-$0.08 |
| Macro | 500K+ | 粉丝数 × $0.08-$0.12 |

**平台系数**：
- YouTube: ×1.0（基准）
- Instagram: ×0.6
- TikTok: ×0.4 ~ ×0.8

**溢价因子**：
- 垂直领域专家: +20-50%
- 高互动率: +10-30%

**LLM 输出解析**：
- 三层降级策略：直接 JSON → Markdown 代码块提取 → 正则匹配
- 价格校验：确保 price_min ≤ price_max，数值非负

---

### 5.3 Writer Agent — 邮件生成引擎

**文件**：`agents/writer.py` (97 行)

**职责**：为已确认的候选人生成个性化商务合作邮件

**邮件结构**：
1. 主题行（Subject）
2. 开场白（引用网红具体内容）
3. 价值主张（品牌合作价值）
4. 行动号召（CTA）
5. 专业签名

**约束**：
- 字数上限: 120 词
- 语调: 自然、个性化、非销售导向
- 支持用户手动编辑和重新生成

---

## 6. 平台数据提供者

采用 **策略模式（Strategy Pattern）**，通过抽象基类统一接口：

```python
class PlatformProvider(ABC):
    platform_name: str           # "YouTube" / "Instagram" / "TikTok"
    search_site_filter: str      # "site:youtube.com/@"

    async def get_stats(url) -> (follower_count, name, engagement_rate)
    def validate_url(url) -> bool
    def extract_handle(url) -> str
```

### 实现对比

| 特性 | YouTube | Instagram | TikTok |
|------|---------|-----------|--------|
| **搜索过滤** | `site:youtube.com/@` | `site:instagram.com` | `site:tiktok.com/@` |
| **验证 API** | YouTube Data API v3 | Graph API (Business Discovery) | Research API (OAuth 2.0) |
| **认证方式** | API Key | Access Token | Client Credentials |
| **必需配置** | `GOOGLE_API_KEY` | `INSTAGRAM_ACCESS_TOKEN` + `USER_ID` | `TIKTOK_CLIENT_KEY` + `SECRET` |
| **降级策略** | forHandle → Search → ID 查询 | 返回 (0, name, 0.0) | 返回 (0, name, 0.0) |
| **缓存** | 内存缓存 (避免重复查询) | 无 | Token 缓存 (~2h 有效期) |

---

## 7. 数据库设计

**引擎**：SQLite（文件存储于 `data/memory.db`）
**ORM**：SQLAlchemy 2.0+

### ER 图

```
┌─────────────────────┐       ┌──────────────────────────────┐
│    SearchBatch      │       │         Influencer           │
├─────────────────────┤       ├──────────────────────────────┤
│ id (PK)             │       │ id (PK)                      │
│ brand_requirement   │1    N │ batch_id (FK → SearchBatch)  │
│ brand_name          │───────│ name                         │
│ platforms           │       │ platform                     │
│ candidate_count     │       │ platform_handle              │
│ created_at          │       │ url (UNIQUE)                 │
└─────────────────────┘       │ follower_count               │
                              │ followers_verified            │
                              │ engagement_rate               │
                              │ tags / niche / language       │
                              │ fit_score (1-100)             │
                              │ fit_reason                    │
                              │ price_min / price_max (USD)   │
                              │ email_draft                   │
                              │ is_confirmed                  │
                              │ error_count                   │
                              │ created_at / updated_at       │
                              └──────────────────────────────┘
```

**索引**：`platform`, `fit_score`, `is_confirmed`, `batch_id`

---

## 8. API 集成

| API | 用途 | 每次运行调用量 | 认证方式 | 成本 |
|-----|------|---------------|---------|------|
| **Google Custom Search** | 网红发现 | 15-30 次 | API Key | ~$5/1000 次 (100 次免费/天) |
| **YouTube Data API v3** | 粉丝验证 | ~50 次 | API Key | 免费 (10K units/天) |
| **Instagram Graph API** | 粉丝验证 | ~50 次 | Access Token | 免费 (需商业账户) |
| **TikTok Research API** | 粉丝验证 | ~50 次 | OAuth 2.0 | 免费 (需审批) |
| **Gemini 2.0 Flash** | 查询/评分/邮件 | 2-15 次 | API Key | ~$0.075/1M input tokens |

---

## 9. 并发模型与性能

### 并发控制

```python
# 全局信号量，限制最大并行 API 调用数
semaphore = asyncio.Semaphore(MAX_CONCURRENT_API)  # 默认: 5

async with semaphore:
    result = await api_call()
```

- 所有 I/O 操作使用 `asyncio` 异步执行
- `asyncio.gather()` 实现批量任务并行
- 信号量防止 API 配额耗尽

### 性能指标

| 阶段 | 耗时 | 并行度 |
|------|------|--------|
| 查询生成 | ~2-3s | 1 (单次 Gemini 调用) |
| 搜索执行 | ~5-10s | 5 并行 |
| 数据采集 | ~10-15s | 5 并行 |
| 批量评分 | ~5-10s/批 | 多批并行 |
| 邮件生成 | ~2-3s/封 | 5 并行 |
| **全流程** | **~30-60s** | — |

### 资源占用

- 内存: ~200-300 MB
- 存储: SQLite 每 100 候选人约 100 KB
- 网络: 每次运行约 100-200 KB

---

## 10. 配置与部署

### 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `GEMINI_API_KEY` | 是 | Google AI Studio 密钥 |
| `GOOGLE_API_KEY` | 是 | Google Cloud 密钥 (Search + YouTube) |
| `SEARCH_ENGINE_ID` | 是 | 可编程搜索引擎 ID |
| `INSTAGRAM_ACCESS_TOKEN` | 否 | Meta Graph API Token |
| `INSTAGRAM_USER_ID` | 否 | Instagram 商业账户 ID |
| `TIKTOK_CLIENT_KEY` | 否 | TikTok 开发者 Key |
| `TIKTOK_CLIENT_SECRET` | 否 | TikTok 开发者 Secret |

### 可调参数 (`config.py`)

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `BATCH_SIZE` | 5 | 每批评分候选人数 |
| `FIT_SCORE_THRESHOLD` | 60 | 最低邮件生成分数 |
| `TOP_PICK_THRESHOLD` | 80 | 最佳推荐标记分数 |
| `EMAIL_WORD_LIMIT` | 120 | 邮件字数上限 |
| `MAX_CONCURRENT_API` | 5 | 最大并行 API 调用数 |
| `SEARCH_RESULTS_PER_QUERY` | 10 | 每次搜索结果数 |
| `QUERIES_PER_PLATFORM` | 5 | 每平台搜索查询数 |

### 部署架构

```
开发环境:
  .env → python-dotenv → 本地 Streamlit
  Dev Container (Python 3.11, VSCode)

生产环境:
  Streamlit Cloud Secrets (TOML) → Streamlit Cloud (无服务器)
  自动部署: GitHub main 分支 push 触发
```

### Streamlit 主题配置

```toml
[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
```

---

## 11. 安全设计

| 安全层面 | 措施 |
|----------|------|
| **密钥管理** | `.env` (本地) / Streamlit Secrets (生产)，不提交 Git |
| **SQL 注入防护** | SQLAlchemy ORM 参数化查询 |
| **API 限流** | asyncio.Semaphore 控制并发，防配额耗尽 |
| **Token 管理** | TikTok OAuth token 内存缓存，自动刷新 |
| **数据隔离** | SQLite 文件级隔离，URL 唯一约束防重复 |
| **错误处理** | 异常捕获 + 优雅降级，不暴露敏感堆栈信息 |

---

> 文档版本: 2.0
> 最后更新: 2026-03-03
> 代码仓库: https://github.com/Gabbyzzzzz/Influencer_Agent_Pro
