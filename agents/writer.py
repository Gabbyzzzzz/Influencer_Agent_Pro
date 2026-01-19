import os
import asyncio
from google import genai
from database import get_db, Influencer
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class WriterAgent:
    def __init__(self):
        self.db = get_db()

    async def write_draft(self, brand_requirement, influencer):
        prompt = f"""
        你是一个专业的海外 PR。
        品牌需求：{brand_requirement}
        网红：{influencer.name} (粉丝: {influencer.follower_count})
        分析理由：{influencer.fit_reason}

        任务：写一封 120 字以内的英文邀约邮件。
        要求：
        1. 第一句要夸奖对方频道的某个特质（基于分析理由）。
        2. 诚邀合作并询问报价。
        3. 语气要像真人，不要像机器人。
        """
        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt
            )
            influencer.email_draft = response.text
            return True
        except:
            return False

    async def run(self, brand_requirement):
        # 为高分博主写信
        pending_list = self.db.query(Influencer).filter(
            Influencer.fit_score >= 60,
            Influencer.email_draft == None
        ).all()

        if not pending_list: return

        tasks = [self.write_draft(brand_requirement, inf) for inf in pending_list]
        await asyncio.gather(*tasks)
        self.db.commit()