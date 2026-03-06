# Centralized configuration
import os
from dotenv import load_dotenv

# 1. Load .env (local dev)
load_dotenv()

# 2. Streamlit Cloud secrets → inject into env vars (deployment)
try:
    import streamlit as st
    for key, val in st.secrets.items():
        if isinstance(val, str) and key not in os.environ:
            os.environ[key] = val
except Exception:
    pass

# Agent config
BATCH_SIZE = 5
FIT_SCORE_THRESHOLD = 60
TOP_PICK_THRESHOLD = 80
EMAIL_WORD_LIMIT = 120

# API concurrency
MAX_CONCURRENT_API = 3          # reduced for Streamlit Cloud memory limits
SEARCH_RESULTS_PER_QUERY = 10
QUERIES_PER_PLATFORM = 5        # balanced for coverage vs memory
MAX_RETRIES = 3

# Supported platforms
SUPPORTED_PLATFORMS = ["YouTube", "Instagram", "TikTok"]
DEFAULT_PLATFORMS = ["YouTube"]

# URL blacklist (cross-platform)
GLOBAL_URL_BLACKLIST = [
    'support.google', 'policies.google', 'help.', 'docs.', 'about',
    'terms', '/results', '/feed', '/discover', '/search', '/playlist',
    '/shorts', '/gaming', '/explore', '/reels', '/stories', '/accounts',
    '/music', '/tag', '.xml', '.pdf', 'robots.txt',
    # Instagram posts/Reels (not profile pages)
    'instagram.com/p/', 'instagram.com/reel/',
    # TikTok videos (not profile pages)
    'tiktok.com/@/video/',
    # YouTube non-profile pages
    '/watch?', '/live/', '/community', '/membership',
]

# UI defaults
DEFAULT_MIN_SCORE = 40
