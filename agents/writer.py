import os
import asyncio
from google import genai
from database import get_db, Influencer
from dotenv import load_dotenv
from utils.logger import get_logger
from config import FIT_SCORE_THRESHOLD, MAX_CONCURRENT_API, EMAIL_WORD_LIMIT

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
logger = get_logger("writer")


class WriterAgent:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_API)

    async def write_draft(self, brand_requirement: str, influencer, brand_name: str = "", brand_website: str = "") -> bool:
        brand_info = ""
        if brand_name:
            brand_info += f"品牌名称：{brand_name}\n"
        if brand_website:
            brand_info += f"品牌网站：{brand_website}\n"

        fit_reason = influencer.fit_reason or "该博主与品牌有良好匹配度"

        prompt = f"""你是一位经验丰富的海外品牌合作经理。
{brand_info}产品/服务需求：{brand_requirement}

目标网红：{influencer.name}
  - 平台：{influencer.platform}
  - 粉丝：{influencer.follower_count:,}
  - 为什么选TA：{fit_reason}

任务：写一封个性化英文邀约邮件（{EMAIL_WORD_LIMIT} words 以内）。
结构：
1. Subject line（引人注目的主题行，单独一行）
2. Opening（提及对方频道的具体内容或特质，展示你做了调研）
3. Value proposition（合作能给对方带来什么价值）
4. CTA（清晰的下一步行动，如安排通话）
5. Sign off（专业但亲切的结尾）

要求：
- 语气自然像真人，不要像机器生成
- 避免空洞的奉承，要有具体的内容引用
- 不要使用 "I hope this email finds you well" 等老套开头"""

        async with self.semaphore:
            try:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.0-flash",
                    contents=prompt
                )
                draft = response.text.strip()

                # 长度校验
                word_count = len(draft.split())
                if word_count > EMAIL_WORD_LIMIT * 1.5:
                    logger.warning(f"邮件过长 ({word_count} words): {influencer.name}，将截取")
                    words = draft.split()[:EMAIL_WORD_LIMIT]
                    draft = ' '.join(words) + '...'

                influencer.email_draft = draft
                logger.info(f"邮件草稿生成成功: {influencer.name} ({word_count} words)")
                return True
            except Exception as e:
                logger.error(f"邮件生成失败 ({influencer.name}): {e}")
                return False

    async def run(self, brand_requirement: str, brand_name: str = "", brand_website: str = ""):
        with get_db() as db:
            pending_list = db.query(Influencer).filter(
                Influencer.is_confirmed == True,
                Influencer.email_draft == None
            ).all()

            if not pending_list:
                logger.info("没有需要生成邮件的候选人")
                return

            logger.info(f"开始生成邮件: {len(pending_list)} 位候选人")

            tasks = [self.write_draft(brand_requirement, inf, brand_name, brand_website) for inf in pending_list]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            success = sum(1 for r in results if r is True)
            logger.info(f"邮件生成完成: {success}/{len(pending_list)} 成功")

            db.commit()
