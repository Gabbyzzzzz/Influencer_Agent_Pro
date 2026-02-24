import os
import asyncio
from typing import List
from googleapiclient.discovery import build
from google import genai
from database import get_db, Influencer, SearchBatch
from dotenv import load_dotenv
from utils.youtube_utils import YouTubeProvider
from utils.instagram_utils import InstagramProvider
from utils.tiktok_utils import TikTokProvider
from utils.logger import get_logger
from config import MAX_CONCURRENT_API, SEARCH_RESULTS_PER_QUERY, QUERIES_PER_PLATFORM, GLOBAL_URL_BLACKLIST

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
logger = get_logger("scout")


class ScoutAgent:
    def __init__(self, platforms: List[str] = None):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("SEARCH_ENGINE_ID")
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_API)

        # 缓存 search service
        self._search_service = build("customsearch", "v1", developerKey=self.google_api_key)

        # 平台 Provider 注册
        self._all_providers = {
            "YouTube": YouTubeProvider(),
            "Instagram": InstagramProvider(),
            "TikTok": TikTokProvider(),
        }
        platform_names = platforms or ["YouTube"]
        self.providers = {p: self._all_providers[p] for p in platform_names if p in self._all_providers}

    async def generate_queries(self, brand_requirement: str, platform_filter: str) -> List[str]:
        prompt = f"""You are an expert influencer search specialist.

Brand requirement: '{brand_requirement}'

Task: Generate {QUERIES_PER_PLATFORM} diverse Google search queries to find influencer profiles.

CRITICAL RULES:
- Every query MUST start with exactly: {platform_filter}
- Use broad, natural English keywords (NOT exact-match quoted phrases)
- Do NOT use operators like +, OR, AND
- Do NOT wrap multiple words in quotes — use bare keywords
- Each query should target a different angle:
  1. Product category keywords (e.g., pet memorial, pet urn, pet accessories)
  2. Creator type keywords (e.g., pet loss support, pet care vlog)
  3. Audience keywords (e.g., dog mom, cat lover, pet parent)
  4. Content style keywords (e.g., pet DIY, pet product review, unboxing)
  5. Niche community keywords (e.g., rainbow bridge, pet grief, pet remembrance)

GOOD examples:
  {platform_filter} pet memorial custom urn review
  {platform_filter} dog lover accessories haul
  {platform_filter} pet loss support grief vlog

BAD examples (DO NOT do this):
  "pet memorial" "custom urn" review OR unboxing
  site:youtube.com/@ + "pet accessories"

Output format: One query per line, no numbering, no extra text."""

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw_queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]

        # 验证并修复：确保每条查询都包含正确的 site: 过滤
        validated = []
        for q in raw_queries:
            if platform_filter not in q:
                q = f"{platform_filter} {q}"
                logger.warning(f"修复缺失 site filter: {q}")
            validated.append(q)

        queries = validated[:QUERIES_PER_PLATFORM]
        logger.info(f"生成 {len(queries)} 条搜索指令 ({platform_filter}): {queries}")
        return queries

    async def execute_search(self, query: str) -> List[dict]:
        async with self.semaphore:
            try:
                res = await asyncio.to_thread(
                    self._search_service.cse().list(
                        q=query, cx=self.search_engine_id, num=SEARCH_RESULTS_PER_QUERY
                    ).execute
                )
                items = res.get('items', [])
                logger.info(f"搜索返回 {len(items)} 条: {query[:60]}...")
                return items
            except Exception as e:
                logger.error(f"搜索失败 ({query[:40]}...): {e}")
                return []

    async def _fetch_single_stats(self, url: str, title: str, snippet: str):
        """获取单个 URL 的统计数据"""
        platform = "Unknown"
        handle = ""
        real_subs = 0
        real_name = title
        engagement_rate = 0.0
        verified = False

        for pname, provider in self.providers.items():
            if provider.validate_url(url):
                platform = pname
                handle = provider.extract_handle(url)
                try:
                    async with self.semaphore:
                        real_subs, fetched_name, engagement_rate = await provider.get_stats(url)
                    if fetched_name:
                        real_name = fetched_name
                    # 粉丝数 > 0 说明 API 成功返回了真实数据
                    if real_subs > 0:
                        verified = True
                except Exception as e:
                    logger.warning(f"获取统计失败 ({url}): {e}")
                break

        return {
            "name": real_name,
            "url": url,
            "platform": platform,
            "platform_handle": handle,
            "follower_count": real_subs,
            "followers_verified": verified,
            "engagement_rate": engagement_rate,
            "tags": snippet,
        }

    async def save_to_discovery(self, all_raw_results: List[dict], batch_id: int = None) -> int:
        # 第一步：过滤和去重
        seen_urls = set()
        valid_items = []

        with get_db() as db:
            existing_urls = {row.url for row in db.query(Influencer.url).all()}

        for item in all_raw_results:
            url = item.get('link')
            if not url:
                continue
            url_lower = url.lower()
            if any(word in url_lower for word in GLOBAL_URL_BLACKLIST):
                continue
            if url in seen_urls or url in existing_urls:
                continue
            seen_urls.add(url)
            valid_items.append(item)

        if not valid_items:
            logger.info("没有新的候选 URL")
            return 0

        logger.info(f"过滤后 {len(valid_items)} 个新 URL，开始并行获取统计...")

        # 第二步：并行获取所有统计数据
        stats_tasks = [
            self._fetch_single_stats(
                item['link'],
                item.get('title', ''),
                item.get('snippet', '')
            )
            for item in valid_items
        ]
        results = await asyncio.gather(*stats_tasks, return_exceptions=True)

        # 第三步：批量写入数据库
        new_count = 0
        with get_db() as db:
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"统计获取异常: {result}")
                    continue
                if batch_id:
                    result["batch_id"] = batch_id
                db.add(Influencer(**result))
                new_count += 1
                logger.info(f"新增: {result['name']} ({result['platform']}, {result['follower_count']:,})")
            # 更新批次的候选人数
            if batch_id:
                batch = db.query(SearchBatch).filter_by(id=batch_id).first()
                if batch:
                    batch.candidate_count = new_count
            db.commit()

        return new_count

    async def run(self, brand_requirement: str, brand_name: str = "", batch_id: int = None) -> int:
        logger.info(f"Scout 启动，平台: {list(self.providers.keys())}")

        # 如果没有传入 batch_id，创建新批次
        if not batch_id:
            with get_db() as db:
                batch = SearchBatch(
                    brand_requirement=brand_requirement,
                    brand_name=brand_name,
                    platforms=",".join(self.providers.keys()),
                )
                db.add(batch)
                db.commit()
                batch_id = batch.id
                logger.info(f"创建搜索批次 #{batch_id}")

        # 所有平台并行生成搜索指令
        query_tasks = [
            self.generate_queries(brand_requirement, provider.search_site_filter)
            for provider in self.providers.values()
        ]
        all_query_lists = await asyncio.gather(*query_tasks)

        # 所有搜索指令并行执行
        all_queries = [q for query_list in all_query_lists for q in query_list]
        logger.info(f"共 {len(all_queries)} 条搜索指令，开始并行搜索...")
        search_tasks = [self.execute_search(q) for q in all_queries]
        results_lists = await asyncio.gather(*search_tasks)

        all_items = [item for result_list in results_lists for item in result_list]
        logger.info(f"搜索阶段完成，共 {len(all_items)} 条原始结果")

        # 并行获取统计 + 保存
        new_count = await self.save_to_discovery(all_items, batch_id=batch_id)
        logger.info(f"Scout 完成！新增 {new_count} 位候选人。")
        return new_count
