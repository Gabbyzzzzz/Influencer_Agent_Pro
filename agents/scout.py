import os
import asyncio
import socket
from googleapiclient.discovery import build
from google import genai
from database import get_db, Influencer
from dotenv import load_dotenv
# --- 导入刚才写的工具函数 ---
from utils.youtube_utils import get_youtube_stats

socket.setdefaulttimeout(30)
load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class ScoutAgent:
    def __init__(self):
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("SEARCH_ENGINE_ID")
        self.db = get_db()

    async def generate_queries(self, brand_requirement):
        prompt = f"""
        品牌需求：'{brand_requirement}'
        任务：生成 3 条针对 YouTube 个人频道主页的搜索指令。
        要求：
        1. 必须包含 site:youtube.com/c/ 或 site:youtube.com/@。
        2. 只输出指令，每行一条。
        """
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.0-flash",
            contents=prompt
        )
        return [q.strip() for q in response.text.strip().split('\n') if q.strip()][:3]

    async def execute_search(self, query):
        try:
            service = build("customsearch", "v1", developerKey=self.google_api_key)
            res = await asyncio.to_thread(
                service.cse().list(q=query, cx=self.search_engine_id, num=5).execute
            )
            return res.get('items', [])
        except Exception as e:
            return []

    def save_to_discovery(self, all_raw_results):
        new_count = 0
        blacklist = ['support.google', 'policies.google', 'help.', 'docs.', 'about', 'terms']

        for item in all_raw_results:
            url = item.get('link')
            if not url or any(word in url.lower() for word in blacklist):
                continue

            existing = self.db.query(Influencer).filter_by(url=url).first()
            if not existing:
                # --- 核心修改：如果是 YouTube 链接，获取真实粉丝数 ---
                real_subs = 0
                real_name = item.get('title')

                if "youtube.com" in url.lower():
                    # 注意：获取粉丝数是网络请求，我们在这里同步调用（或用 to_thread）
                    real_subs, fetched_name = get_youtube_stats(url)
                    if fetched_name: real_name = fetched_name

                new_influencer = Influencer(
                    name=real_name,
                    url=url,
                    platform="YouTube" if "youtube.com" in url.lower() else "Instagram",
                    follower_count=real_subs,  # 存入真实数字
                    tags=item.get('snippet')
                )
                self.db.add(new_influencer)
                new_count += 1

        self.db.commit()
        return new_count

    async def run(self, brand_requirement):
        print(f"🕵️ Scout 深度侦查启动 (包含粉丝数校对)...")
        queries = await self.generate_queries(brand_requirement)
        search_tasks = [self.execute_search(q) for q in queries]
        search_results_lists = await asyncio.gather(*search_tasks)

        all_items = []
        for result_list in search_results_lists:
            all_items.extend(result_list)

        # 保存并获取统计数据
        new_count = self.save_to_discovery(all_items)
        print(f"✅ Scout 完成！人才库新增 {new_count} 位经过数据核实的候选人。")
        return new_count