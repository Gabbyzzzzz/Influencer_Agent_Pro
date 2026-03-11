# InfluencerScout — 项目介绍

## 一句话简介

InfluencerScout 是一个 AI 驱动的网红营销自动化工具，帮助品牌方在 YouTube、Instagram、TikTok 上一键完成网红发现、评分筛选和邮件外联。

**在线体验**: [Live Demo](https://gabbyzzzzz-influencer-agent-pro-app-f5eohp.streamlit.app/)
**代码仓库**: [GitHub](https://github.com/Gabbyzzzzz/Influencer_Agent_Pro)

---

## 解决什么问题

传统的网红营销合作流程需要大量人工操作：

| 环节 | 传统方式 | InfluencerScout |
|------|---------|-----------------|
| 发现网红 | 手动在各平台搜索、逐个浏览 | AI 生成搜索策略，跨平台批量发现 |
| 评估匹配度 | 凭经验主观判断 | LLM 智能评分（1-100），附评分理由 |
| 估算报价 | 询价或猜测 | 基于粉丝量级 + 平台系数自动估价 |
| 撰写邮件 | 逐封手写 | AI 生成个性化合作邮件，可编辑 |
| **总耗时** | **数小时 ~ 数天** | **约 1 分钟** |

---

## 核心功能

### 1. 智能发现 (Scout Agent)
- 输入品牌需求，AI 自动生成多角度搜索关键词
- 通过 Google Custom Search 跨 YouTube / Instagram / TikTok 三平台搜索
- 自动调用平台 API 获取真实粉丝数，过滤无效链接

### 2. 智能评分 (Analyst Agent)
- Gemini 2.0 Flash 对每位候选人进行品牌契合度评分（1-100 分）
- 基于粉丝量级和平台类型自动估算合作报价
- 分批处理 + JSON 多层解析，保证输出稳定可靠

### 3. 邮件生成 (Writer Agent)
- 为确认的候选人生成个性化英文合作邮件
- 包含主题行、开场白、价值主张、行动号召
- 支持在线编辑和重新生成

### 4. 交互式 UI
- Streamlit 构建的现代化 Web 界面
- 候选人表格支持排序、筛选、勾选确认
- 一键导出 CSV（候选人数据）和 TXT（邮件合集）

---

## 系统架构

```
用户输入 (品牌需求 + 平台 + 预算)
        │
        v
  ┌─────────────┐     Google Custom Search
  │ Scout Agent │────▶ YouTube Data API v3
  │  网红发现    │     Instagram / TikTok API
  └──────┬──────┘
         │ 候选人入库
         v
  ┌──────────────┐
  │Analyst Agent │────▶ Gemini 2.0 Flash
  │ 评分 & 定价   │     (品牌契合度 + 报价)
  └──────┬───────┘
         │ 用户筛选确认
         v
  ┌─────────────┐
  │Writer Agent │────▶ Gemini 2.0 Flash
  │  邮件生成    │     (个性化合作邮件)
  └──────┬──────┘
         │
         v
  导出 CSV / TXT
```

三个 Agent 各司其职，通过 SQLite 数据库共享数据，用户通过 Streamlit UI 控制全流程。

---

## 技术栈

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| AI 模型 | Google Gemini 2.0 Flash | 搜索词生成、评分推理、邮件撰写 |
| 搜索引擎 | Google Custom Search API | 跨平台网红发现 |
| 数据验证 | YouTube Data API v3 | 粉丝数实时校验 |
| 后端 | Python 3.11 + asyncio | 异步并发，信号量控速 |
| 数据库 | SQLite + SQLAlchemy 2.0 | 轻量持久化 |
| 前端 | Streamlit | 交互式 Web 界面 |
| 部署 | Streamlit Cloud | GitHub push 自动部署 |

---

## 项目亮点

1. **多 Agent 协作架构** — Scout / Analyst / Writer 三个 Agent 职责分离，流水线式协作，易于扩展
2. **LLM 输出的工程化处理** — 三层 JSON 解析降级策略（直接解析 → 代码块提取 → 正则匹配），确保 AI 输出稳定可用
3. **跨平台统一抽象** — 策略模式（Strategy Pattern）封装 YouTube / Instagram / TikTok 数据提供者，新增平台只需实现接口
4. **异步并发控制** — asyncio + Semaphore 实现 API 调用的并行 + 限流，兼顾性能和配额
5. **全流程自动化** — 从搜索发现到邮件生成，用户只需输入品牌需求，一键完成

---

## 使用示例

**输入**:
> Brand: DecorJoy
> Requirement: Home decor and interior design brand — we sell wall art, throw pillows, candles, and decorative accessories. Looking for home decor YouTubers, room makeover creators, and cozy home aesthetic channels. Target market: US homeowners.
> Platform: YouTube
> Budget: $1,000 – $10,000

**输出**:
- 发现 20-50 位 home decor 领域 YouTuber
- 每位候选人有品牌契合度评分、粉丝数、预估报价
- 勾选确认后自动生成个性化合作邮件

---

## 项目结构

```
InfluencerScout/
├── app.py                 # 主应用入口 (Streamlit UI + 流程编排)
├── config.py              # 集中配置
├── database.py            # 数据库模型 (SQLAlchemy ORM)
├── agents/
│   ├── scout.py           # 发现 Agent
│   ├── analyst.py         # 评分 Agent
│   └── writer.py          # 邮件 Agent
├── utils/
│   ├── platform_base.py   # 平台提供者抽象基类
│   ├── youtube_utils.py   # YouTube 数据提供者
│   ├── instagram_utils.py # Instagram 数据提供者
│   └── tiktok_utils.py    # TikTok 数据提供者
└── data/
    └── memory.db          # SQLite 数据库
```

代码总量约 1,500 行 Python。

---

## 当前状态与未来规划

### 平台接入状态

| 能力 | YouTube | Instagram | TikTok |
|------|---------|-----------|--------|
| 搜索发现 | ✅ 已上线 | ✅ 已上线 | ✅ 已上线 |
| 粉丝数验证 | ✅ YouTube Data API v3 | ⏳ 代码已完成，需配置 Graph API token | ⏳ 代码已完成，需 Research API 审批 |
| 互动率 | ❌ 暂未实现 | ❌ 暂未实现 | ✅ 基于点赞/视频数估算 |

> **说明**：三个平台的搜索发现均通过 Google Custom Search 实现，开箱即用。粉丝数验证方面，YouTube 已完整接入，Instagram 和 TikTok 的代码逻辑已写好（策略模式统一接口），配置对应 API credentials 即可启用。未配置时会优雅降级——粉丝数显示为 "Unverified"，不影响搜索和评分流程。

### 未来规划

- **Instagram / TikTok 数据完善** — 接入 Graph API 和 Research API，获取真实粉丝数和互动率
- **互动率分析** — 引入 YouTube 频道近期视频的点赞/评论数据，计算真实互动率
- **邮件发送集成** — 对接 Gmail API 或 SendGrid，支持一键发送合作邮件
- **批量历史对比** — 多次搜索结果对比，追踪候选人数据变化
- **用户账户系统** — 支持多品牌/多用户管理
