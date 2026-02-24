from abc import ABC, abstractmethod
from typing import List, Tuple


class PlatformProvider(ABC):
    """所有平台 Provider 的基类"""

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """平台名称，如 'YouTube', 'Instagram'"""

    @property
    @abstractmethod
    def search_site_filter(self) -> str:
        """Google 搜索的 site: 限定，如 'site:youtube.com/@'"""

    @abstractmethod
    async def get_stats(self, url: str) -> Tuple[int, str, float]:
        """
        获取频道/账号统计数据
        返回: (follower_count, channel_name, engagement_rate)
        """

    @abstractmethod
    def validate_url(self, url: str) -> bool:
        """验证 URL 是否属于该平台"""

    @abstractmethod
    def extract_handle(self, url: str) -> str:
        """从 URL 提取平台用户名 (@handle)"""
