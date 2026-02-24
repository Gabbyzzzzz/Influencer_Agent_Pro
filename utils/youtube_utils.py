import os
import re
import asyncio
from typing import Tuple
from googleapiclient.discovery import build
from dotenv import load_dotenv
from utils.platform_base import PlatformProvider
from utils.logger import get_logger

load_dotenv()
logger = get_logger("youtube")

# 缓存：避免重复 API 调用
_stats_cache: dict = {}

# 缓存 YouTube service 对象（build() 很慢，只需初始化一次）
_youtube_service = None


def _get_youtube_service():
    global _youtube_service
    if _youtube_service is None:
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            _youtube_service = build("youtube", "v3", developerKey=api_key)
    return _youtube_service


class YouTubeProvider(PlatformProvider):

    @property
    def platform_name(self) -> str:
        return "YouTube"

    @property
    def search_site_filter(self) -> str:
        return "site:youtube.com/@"

    def validate_url(self, url: str) -> bool:
        return "youtube.com" in url.lower()

    def extract_handle(self, url: str) -> str:
        """从 YouTube URL 提取 @handle 或 /c/name"""
        m = re.search(r'youtube\.com/@([\w\-\.]+)', url, re.IGNORECASE)
        if m:
            return f"@{m.group(1)}"
        m = re.search(r'youtube\.com/c/([\w\-\.]+)', url, re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r'youtube\.com/channel/([\w\-]+)', url, re.IGNORECASE)
        if m:
            return m.group(1)
        return ""

    async def get_stats(self, url: str) -> Tuple[int, str, float]:
        """获取 YouTube 频道统计。使用缓存 + 单例 service。"""
        if url in _stats_cache:
            return _stats_cache[url]

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or not self.validate_url(url):
            return 0, "", 0.0

        try:
            result = await asyncio.to_thread(self._fetch_stats_sync, url)
            _stats_cache[url] = result
            return result
        except Exception as e:
            logger.error(f"YouTube API 错误 ({url}): {e}")
            return 0, "", 0.0

    def _fetch_stats_sync(self, url: str) -> Tuple[int, str, float]:
        """同步获取频道统计（在线程中运行），复用全局 service"""
        youtube = _get_youtube_service()
        if not youtube:
            return 0, "", 0.0

        handle = self.extract_handle(url)

        # 方式1: @handle → forHandle 直接查询（1 次 API）
        if handle.startswith("@"):
            try:
                res = youtube.channels().list(
                    forHandle=handle[1:],
                    part="id,snippet,statistics"
                ).execute()
                if res.get('items'):
                    item = res['items'][0]
                    stats = item['statistics']
                    subs = int(stats.get('subscriberCount', 0))
                    name = item['snippet']['title']
                    logger.info(f"查询成功: {handle} → {name} ({subs:,})")
                    return subs, name, 0.0
            except Exception as e:
                logger.warning(f"forHandle 失败 ({handle}), fallback: {e}")

        # 方式2: /channel/UCxxxx → 直接用 ID
        channel_id = handle if (handle and handle.startswith("UC")) else None
        channel_name = ""

        # 方式3: fallback → 搜索
        if not channel_id:
            search_res = youtube.search().list(
                q=url, type="channel", part="id,snippet", maxResults=1
            ).execute()
            if not search_res.get('items'):
                logger.warning(f"搜索未找到: {url}")
                return 0, "", 0.0
            channel_id = search_res['items'][0]['id']['channelId']
            channel_name = search_res['items'][0]['snippet']['title']

        detail_res = youtube.channels().list(
            id=channel_id, part="statistics,snippet"
        ).execute()
        if not detail_res.get('items'):
            return 0, channel_name, 0.0

        item = detail_res['items'][0]
        subs = int(item['statistics'].get('subscriberCount', 0))
        name = item['snippet']['title'] or channel_name
        logger.info(f"查询成功: {name} ({subs:,})")
        return subs, name, 0.0


# 向后兼容
_provider = YouTubeProvider()


def get_youtube_stats(url: str) -> Tuple[int, str]:
    """兼容旧接口"""
    if not os.getenv("GOOGLE_API_KEY") or "youtube.com" not in url.lower():
        return 0, ""
    subs, name, _ = _provider._fetch_stats_sync(url)
    return subs, name
