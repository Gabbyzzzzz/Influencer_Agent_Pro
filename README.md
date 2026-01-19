# 🐾 Influencer Sourcing Agent Pro

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Model](https://img.shields.io/badge/Model-Gemini%202.0%20Flash-orange?logo=google-gemini&logoColor=white)](https://aistudio.google.com/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**Influencer Sourcing Agent Pro** 是一款基于 Google Gemini 2.0 Flash 引擎开发的端到端智能网红营销代理系统。它采用 **Multi-Agent (多智能体)** 协作架构，能够自动完成从“海选搜索”到“深度分析”再到“邀约外联”的全业务流程。

---

## 🚀 核心功能 (Core Features)

本项目严格按照网红营销商务闭环开发，涵盖以下功能模块：

*   **3.1 Discovery (网红发现)**: 
    *   利用 `Scout Agent` 与 Google Search API 协作，精准定位 YouTube/Instagram 个人频道。
    *   内置 URL 黑名单过滤系统，自动剔除官方政策、帮助文档等无效链接。
*   **3.2 Fit Score (契合度评分)**: 
    *   由 `Analyst Agent` 基于品牌需求进行逻辑推理，提供 1-100 分的量化指标。
    *   提供深度推荐理由，解决“为什么他适合我们”的问题。
*   **3.3 Real-time Stats & Price (实时数据与定价)**: 
    *   集成 **YouTube Data API v3**，自动查询博主真实的 `subscriberCount`（粉丝数）。
    *   基于算法公式与 AI 行业经验，预测博主单条视频的合作价格范围。
*   **3.5 Outreach Draft (个性化邀约)**: 
    *   由 `Writer Agent` 根据博主调性与历史内容，生成一对一的英文合作邀约邮件。
*   **3.6 Preview + Confirm (预览与确认)**: 
    *   可视化交互仪表盘，支持在网页端直接预览数据、点击链接并手动勾选“确认”合作状态。
*   **3.7 Top Pick Recommendation (最佳推荐)**: 
    *   系统会自动从海选库中高亮展示分数最高、匹配度最强的博主，并进行重点分析。

---

## 🏗️ 系统架构 (Architecture)

系统采用 **“分层代理 + 长期记忆”** 的设计模式：

1.  **UI 层 (Streamlit)**: 响应式前端界面，支持品牌需求输入与数据实时展示。
2.  **Agentic Layer (多智能体层)**:
    *   `Scout Agent`: 负责广度搜索、API 调度与原始数据清洗。
    *   `Analyst Agent`: 负责批量数据处理、逻辑打分与身价预测。
    *   `Writer Agent`: 负责根据分析报告生成个性化文案。
3.  **Data Layer (存储层)**: 
    *   使用 **SQLAlchemy + SQLite** 实现“长期记忆”，确保所有搜寻到的网红资源永久存储，支持任务隔离与状态同步。

---

## 📂 项目结构 (File Structure)

```text
Influencer_Agent_Pro/
├── agents/             # 各角色的 Agent 逻辑实现
│   ├── scout.py        # 负责发现与搜索
│   ├── analyst.py      # 负责评估与打分
│   └── writer.py       # 负责文案生成
├── data/               # 数据存储空间
│   └── memory.db       # SQLite 长期记忆数据库
├── utils/              # 外部 API 交互工具
│   └── youtube_utils.py # YouTube Data API 封装
├── app.py              # 整个程序的 Streamlit UI 入口
├── database.py         # 数据库模型与 ORM 定义
├── requirements.txt    # 项目依赖清单
└── .env                # 敏感 API 密钥配置 (不上传)
