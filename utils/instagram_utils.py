import os
import re
import asyncio
import urllib.request
import json
from typing import Tuple
from utils.platform_base import PlatformProvider
from utils.logger import get_logger

logger = get_logger("instagram")


class InstagramProvider(PlatformProvider):
    """
    Instagram Provider。
    - 发现：通过 Google Custom Search
    - 统计：通过 Instagram Graph API (Business Discovery)

    需要环境变量：
    - INSTAGRAM_ACCESS_TOKEN: Meta Graph API access token
    - INSTAGRAM_USER_ID: 你自己的 Instagram Business 账号 ID（用于发起 business_discovery 查询）

    申请步骤：
    1. https://developers.facebook.com/ 创建 App
    2. 添加 Instagram Graph API 产品
    3. 在 Graph API Explorer 中获取 token（勾选 instagram_basic, business_management）
    4. 用 /me/accounts 找到你的 Instagram Business 账号 ID
    """

    @property
    def platform_name(self) -> str:
        return "Instagram"

    @property
    def search_site_filter(self) -> str:
        return "site:instagram.com"

    def validate_url(self, url: str) -> bool:
        return "instagram.com" in url.lower()

    def extract_handle(self, url: str) -> str:
        """从 Instagram URL 提取用户名"""
        m = re.search(r'instagram\.com/([a-zA-Z0-9_\.]+)', url, re.IGNORECASE)
        if m:
            handle = m.group(1)
            excluded = {'p', 'reel', 'reels', 'explore', 'stories', 'accounts', 'about', 'directory', 'tv'}
            if handle.lower() not in excluded:
                return f"@{handle}"
        return ""

    async def get_stats(self, url: str) -> Tuple[int, str, float]:
        """
        通过 Instagram Graph API Business Discovery 获取公开商业账号数据。
        如果未配置 token，返回基础信息（粉丝数为 0）。
        """
        handle = self.extract_handle(url)
        if not handle:
            return 0, "", 0.0

        username = handle.lstrip("@")
        access_token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        user_id = os.getenv("INSTAGRAM_USER_ID")

        if not access_token or not user_id:
            logger.info(f"Instagram 发现: @{username} (未配置 Graph API token，粉丝数待补充)")
            return 0, username, 0.0

        try:
            result = await asyncio.to_thread(
                self._fetch_business_discovery, username, user_id, access_token
            )
            return result
        except Exception as e:
            logger.warning(f"Instagram API 查询失败 (@{username}): {e}")
            return 0, username, 0.0

    def _fetch_business_discovery(self, username: str, user_id: str, access_token: str) -> Tuple[int, str, float]:
        """通过 Business Discovery 端点获取公开商业账号数据"""
        fields = f"business_discovery.username({username}){{username,name,followers_count,media_count,biography}}"
        api_url = (
            f"https://graph.facebook.com/v21.0/{user_id}"
            f"?fields={fields}"
            f"&access_token={access_token}"
        )

        req = urllib.request.Request(api_url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        biz = data.get("business_discovery", {})
        followers = biz.get("followers_count", 0)
        name = biz.get("name", username)
        media_count = biz.get("media_count", 0)

        # 简单估算互动率（后续可用 media edge 获取精确值）
        engagement = 0.0

        logger.info(f"Instagram 查询成功: @{username} → {name} ({followers:,} followers, {media_count} posts)")
        return followers, name, engagement
