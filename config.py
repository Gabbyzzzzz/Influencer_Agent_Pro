# 集中管理所有可调参数
import os
from dotenv import load_dotenv

# 1. 加载本地 .env（开发环境）
load_dotenv()

# 2. Streamlit Cloud secrets → 注入环境变量（部署环境）
try:
    import streamlit as st
    for key, val in st.secrets.items():
        if isinstance(val, str) and key not in os.environ:
            os.environ[key] = val
except Exception:
    pass

# Agent 配置
BATCH_SIZE = 5
FIT_SCORE_THRESHOLD = 60
TOP_PICK_THRESHOLD = 80
EMAIL_WORD_LIMIT = 120

# API 并发控制
MAX_CONCURRENT_API = 5
SEARCH_RESULTS_PER_QUERY = 10  # 每条搜索返回结果数（原来 5 太少）
QUERIES_PER_PLATFORM = 5      # 每个平台生成搜索指令数（原来 3 太少）
MAX_RETRIES = 3

# 支持的平台
SUPPORTED_PLATFORMS = ["YouTube", "Instagram", "TikTok"]
DEFAULT_PLATFORMS = ["YouTube"]

# URL 黑名单（各平台通用）
GLOBAL_URL_BLACKLIST = [
    'support.google', 'policies.google', 'help.', 'docs.', 'about',
    'terms', '/results', '/feed', '/discover', '/search', '/playlist',
    '/shorts', '/gaming', '/explore', '/reels', '/stories', '/accounts',
    '/music', '/tag', '.xml', '.pdf', 'robots.txt',
    # Instagram 帖子/Reel（不是博主主页）
    'instagram.com/p/', 'instagram.com/reel/',
    # TikTok 视频（不是博主主页）
    'tiktok.com/@/video/',
]

# UI 默认筛选
DEFAULT_MIN_SCORE = 40  # 默认隐藏低分候选人
