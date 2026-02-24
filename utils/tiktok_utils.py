import os
import re
import asyncio
import urllib.request
import json
from typing import Tuple
from utils.platform_base import PlatformProvider
from utils.logger import get_logger

logger = get_logger("tiktok")

# 缓存 TikTok access token（有效期通常 2 小时）
_tiktok_token: str = ""
_tiktok_token_expires: float = 0


class TikTokProvider(PlatformProvider):
    """
    TikTok Provider。
    - 发现：通过 Google Custom Search
    - 统计：通过 TikTok Research API (User Info)

    需要环境变量：
    - TIKTOK_CLIENT_KEY: TikTok 开发者 Client Key
    - TIKTOK_CLIENT_SECRET: TikTok 开发者 Client Secret

    申请步骤：
    1. https://developers.tiktok.com/ 注册开发者账号
    2. 创建 App → 申请 Research API 权限
    3. 等待审批（通常 1-3 天）
    4. 获取 Client Key 和 Client Secret
    """

    @property
    def platform_name(self) -> str:
        return "TikTok"

    @property
    def search_site_filter(self) -> str:
        return "site:tiktok.com/@"

    def validate_url(self, url: str) -> bool:
        return "tiktok.com" in url.lower()

    def extract_handle(self, url: str) -> str:
        """从 TikTok URL 提取用户名"""
        m = re.search(r'tiktok\.com/@([\w\.\-]+)', url, re.IGNORECASE)
        if m:
            return f"@{m.group(1)}"
        return ""

    async def get_stats(self, url: str) -> Tuple[int, str, float]:
        """
        通过 TikTok Research API 获取创作者数据。
        如果未配置 credentials，返回基础信息。
        """
        handle = self.extract_handle(url)
        if not handle:
            return 0, "", 0.0

        username = handle.lstrip("@")
        client_key = os.getenv("TIKTOK_CLIENT_KEY")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET")

        if not client_key or not client_secret:
            logger.info(f"TikTok 发现: @{username} (未配置 Research API，粉丝数待补充)")
            return 0, username, 0.0

        try:
            token = await asyncio.to_thread(
                self._get_access_token, client_key, client_secret
            )
            if not token:
                return 0, username, 0.0

            result = await asyncio.to_thread(
                self._fetch_user_info, username, token
            )
            return result
        except Exception as e:
            logger.warning(f"TikTok API 查询失败 (@{username}): {e}")
            return 0, username, 0.0

    def _get_access_token(self, client_key: str, client_secret: str) -> str:
        """获取 TikTok client access token (OAuth 2.0 client_credentials)"""
        global _tiktok_token, _tiktok_token_expires
        import time

        # 如果 token 还没过期，直接返回
        if _tiktok_token and time.time() < _tiktok_token_expires:
            return _tiktok_token

        body = json.dumps({
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "client_credentials"
        }).encode()

        req = urllib.request.Request(
            "https://open.tiktokapis.com/v2/oauth/token/",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        _tiktok_token = data.get("access_token", "")
        expires_in = data.get("expires_in", 7200)
        _tiktok_token_expires = time.time() + expires_in - 60  # 提前 60 秒过期

        if _tiktok_token:
            logger.info(f"TikTok access token 获取成功 (有效期 {expires_in}s)")
        else:
            logger.error(f"TikTok token 获取失败: {data}")

        return _tiktok_token

    def _fetch_user_info(self, username: str, access_token: str) -> Tuple[int, str, float]:
        """
        调用 TikTok Research API 获取用户信息。
        POST https://open.tiktokapis.com/v2/research/user/info/
        """
        fields = "display_name,bio_description,is_verified,follower_count,following_count,likes_count,video_count"
        api_url = f"https://open.tiktokapis.com/v2/research/user/info/?fields={fields}"

        body = json.dumps({"username": username}).encode()
        req = urllib.request.Request(
            api_url,
            data=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        if data.get("error", {}).get("code") != "ok":
            error_msg = data.get("error", {}).get("message", "未知错误")
            logger.warning(f"TikTok API 错误 (@{username}): {error_msg}")
            return 0, username, 0.0

        user_data = data.get("data", {})
        followers = user_data.get("follower_count", 0)
        display_name = user_data.get("display_name", username)
        likes = user_data.get("likes_count", 0)
        videos = user_data.get("video_count", 0)

        # 估算互动率: 总点赞 / (总视频 * 粉丝数)
        engagement = 0.0
        if followers > 0 and videos > 0:
            avg_likes_per_video = likes / videos
            engagement = round((avg_likes_per_video / followers) * 100, 2)

        logger.info(
            f"TikTok 查询成功: @{username} → {display_name} "
            f"({followers:,} followers, {videos} videos, {engagement}% engagement)"
        )
        return followers, display_name, engagement
