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
logger = get_logger("scout")

_gemini_client = None
def _get_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


class ScoutAgent:
    def __init__(self, platforms: List[str] = None):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("SEARCH_ENGINE_ID")
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_API)

        self._search_service = build("customsearch", "v1", developerKey=self.google_api_key)

        self._all_providers = {
            "YouTube": YouTubeProvider(),
            "Instagram": InstagramProvider(),
            "TikTok": TikTokProvider(),
        }
        platform_names = platforms or ["YouTube"]
        self.providers = {p: self._all_providers[p] for p in platform_names if p in self._all_providers}

    async def generate_queries(self, brand_requirement: str, platform_filter: str, brand_name: str = "") -> List[str]:
        brand_context = f"Brand: {brand_name}\n" if brand_name else ""
        prompt = f"""You are an expert influencer search specialist.

{brand_context}Brand requirement: '{brand_requirement}'

Task: Generate {QUERIES_PER_PLATFORM} diverse Google search queries to find influencer profiles on this platform.

CRITICAL RULES:
- Every query MUST start with exactly: {platform_filter}
- Use broad, natural English keywords (NOT exact-match quoted phrases)
- Do NOT use operators like +, OR, AND, or quotes
- Each query MUST target a DIFFERENT angle to maximize diversity:

  1. Core niche keywords — directly describe the product/service category
  2. Creator type — the kind of influencer (reviewer, vlogger, educator, enthusiast)
  3. Audience persona — who watches this content (e.g. "dog mom", "new parent", "fitness beginner")
  4. Content format — the type of videos/posts (haul, unboxing, tutorial, review, day in life)
  5. Adjacent niche or problem/solution — related topics or problems the brand solves

Make queries SPECIFIC and LONG (4-7 keywords each). Avoid generic terms like "best" or "top".
Vary the vocabulary across queries — do NOT repeat the same keywords.

GOOD examples for a pet memorial brand:
  {platform_filter} pet memorial custom urn creator review
  {platform_filter} dog mom grief loss support vlog
  {platform_filter} pet remembrance keepsake unboxing haul
  {platform_filter} rainbow bridge pet tribute heartfelt
  {platform_filter} pet lover accessories gift guide
  {platform_filter} veterinarian pet loss coping advice
  {platform_filter} animal rescue advocate tribute content

BAD examples (DO NOT do this):
  "pet memorial" "custom urn" review OR unboxing
  {platform_filter} best pet channels

Output format: One query per line, no numbering, no extra text."""

        response = await asyncio.to_thread(
            _get_client().models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt
        )
        raw_queries = [q.strip() for q in response.text.strip().split('\n') if q.strip()]

        validated = []
        for q in raw_queries:
            if platform_filter not in q:
                q = f"{platform_filter} {q}"
                logger.warning(f"Fixed missing site filter: {q}")
            validated.append(q)

        queries = validated[:QUERIES_PER_PLATFORM]
        logger.info(f"Generated {len(queries)} queries ({platform_filter}): {queries}")
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
                logger.info(f"Search returned {len(items)} results: {query[:60]}...")
                return items
            except Exception as e:
                logger.error(f"Search failed ({query[:40]}...): {e}")
                return []

    async def _fetch_single_stats(self, url: str, title: str, snippet: str):
        """Fetch stats for a single URL."""
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
                    if real_subs > 0:
                        verified = True
                except Exception as e:
                    logger.warning(f"Stats fetch failed ({url}): {e}")
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
        # Step 1: Filter and dedup
        seen_urls = set()
        valid_items = []

        # Only dedup within this batch — allow re-discovery across batches
        # But still check DB to avoid exact duplicates (unique constraint)
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
            logger.info("No new candidate URLs found")
            return 0

        logger.info(f"After filtering: {len(valid_items)} new URLs, fetching stats...")

        # Step 2: Parallel stats fetch
        stats_tasks = [
            self._fetch_single_stats(
                item['link'],
                item.get('title', ''),
                item.get('snippet', '')
            )
            for item in valid_items
        ]
        results = await asyncio.gather(*stats_tasks, return_exceptions=True)

        # Step 3: Batch insert to DB
        new_count = 0
        with get_db() as db:
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Stats fetch exception: {result}")
                    continue
                if result.get("platform") == "Unknown":
                    continue
                if batch_id:
                    result["batch_id"] = batch_id
                db.add(Influencer(**result))
                new_count += 1
                logger.info(f"Added: {result['name']} ({result['platform']}, {result['follower_count']:,})")
            if batch_id:
                batch = db.query(SearchBatch).filter_by(id=batch_id).first()
                if batch:
                    batch.candidate_count = new_count
            db.commit()

        return new_count

    async def run(self, brand_requirement: str, brand_name: str = "", batch_id: int = None) -> tuple:
        """Returns (new_count, batch_id) so the UI can auto-focus on the new batch."""
        logger.info(f"Scout starting, platforms: {list(self.providers.keys())}")

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
                logger.info(f"Created search batch #{batch_id}")

        # Generate queries for all platforms in parallel
        query_tasks = [
            self.generate_queries(brand_requirement, provider.search_site_filter, brand_name)
            for provider in self.providers.values()
        ]
        all_query_lists = await asyncio.gather(*query_tasks)

        # Execute all search queries in parallel
        all_queries = [q for query_list in all_query_lists for q in query_list]
        logger.info(f"Total {len(all_queries)} queries, searching in parallel...")
        search_tasks = [self.execute_search(q) for q in all_queries]
        results_lists = await asyncio.gather(*search_tasks)

        all_items = [item for result_list in results_lists for item in result_list]
        logger.info(f"Search phase complete, {len(all_items)} raw results")

        new_count = await self.save_to_discovery(all_items, batch_id=batch_id)
        logger.info(f"Scout complete! Added {new_count} candidates.")
        return new_count, batch_id
