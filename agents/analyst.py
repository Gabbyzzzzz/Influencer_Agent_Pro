import os
import asyncio
import json
import re
from google import genai
from database import get_db, Influencer
from dotenv import load_dotenv
from utils.logger import get_logger
from config import BATCH_SIZE, MAX_CONCURRENT_API

load_dotenv()
logger = get_logger("analyst")

_gemini_client = None
def _get_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _gemini_client


class AnalystAgent:
    def __init__(self):
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_API)

    def _parse_json_response(self, text: str) -> list:
        """多层降级 JSON 解析：直接解析 → 代码块提取 → 正则提取"""
        # 尝试1: 直接解析
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # 尝试2: 提取 markdown 代码块中的 JSON
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            try:
                result = json.loads(m.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # 尝试3: 非贪婪正则匹配第一个 JSON 数组
        m = re.search(r'\[[\s\S]*?\](?=\s*$|\s*[^,\]\}])', text)
        if m:
            try:
                result = json.loads(m.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        logger.warning(f"JSON 解析全部失败，原始响应: {text[:300]}...")
        return []

    def _validate_score(self, res: dict) -> dict:
        """校验并修正 AI 输出的评分数据"""
        score = res.get('fit_score')
        if score is not None:
            score = max(1, min(100, int(score)))
            res['fit_score'] = score

        p_min = res.get('price_min')
        p_max = res.get('price_max')
        if p_min is not None and p_max is not None:
            p_min = max(0, float(p_min))
            p_max = max(0, float(p_max))
            if p_min > p_max:
                p_min, p_max = p_max, p_min
            res['price_min'] = p_min
            res['price_max'] = p_max

        reason = res.get('fit_reason', '')
        if reason and len(reason) > 500:
            res['fit_reason'] = reason[:500]

        return res

    async def analyze_batch(self, brand_requirement: str, influencers: list, budget_range: tuple = None) -> bool:
        inf_list_text = ""
        for i, inf in enumerate(influencers):
            snippet = (inf.tags or '')[:300]
            verified_tag = "✓已验证" if inf.followers_verified else "未验证"
            inf_list_text += (
                f"ID: {i} | 名称: {inf.name} | 平台: {inf.platform} | "
                f"粉丝数: {inf.follower_count:,} ({verified_tag}) | 简介: {snippet}\n"
            )

        budget_hint = ""
        if budget_range:
            budget_hint = f"\n品牌预算范围: ${budget_range[0]:,} - ${budget_range[1]:,} USD\n"

        prompt = f"""你是一个资深的海外营销专家。品牌需求：'{brand_requirement}'
{budget_hint}
待评估博主列表：
{inf_list_text}

任务：
1. Fit Score: 1-100 评分（考虑粉丝量、内容垂直度与需求的匹配度）。
2. Price Range: 按以下分级标准预测单条合作价格(USD)：

   **定价分级表（按粉丝量级）：**
   - Nano（<10K 粉丝）: $50-$200（固定底价区间）
   - Micro（10K-100K）: 粉丝数 × $0.02-$0.05
   - Mid（100K-500K）: 粉丝数 × $0.05-$0.08
   - Macro（500K+）: 粉丝数 × $0.08-$0.12

   **平台系数：**
   - YouTube 长视频: ×1.0（基准）
   - Instagram 帖子/Reel: ×0.6
   - TikTok 短视频: ×0.4（但高互动率可 ×0.6-0.8）

   **溢价因素：** 垂类博主 +20-50%，高互动率 +10-30%
   **重要：** 如果粉丝数为 0 且标注"未验证"，设 price_min=0, price_max=0（表示需确认粉丝数后估价）

3. Fit Reason: 简短说明推荐/不推荐的理由（中文，50字以内）。

示例输出格式：
[
  {{"id": 0, "fit_score": 85, "fit_reason": "该频道专注户外装备评测，与品牌高度契合", "price_min": 500, "price_max": 1200}},
  {{"id": 1, "fit_score": 30, "fit_reason": "内容主题与品牌关联度较低", "price_min": 50, "price_max": 100}},
  {{"id": 2, "fit_score": 70, "fit_reason": "宠物领域博主但粉丝数未验证", "price_min": 0, "price_max": 0}}
]

请严格以 JSON 数组输出，不要有额外文字。"""

        async with self.semaphore:
            try:
                response = await asyncio.to_thread(
                    _get_client().models.generate_content,
                    model="gemini-2.0-flash",
                    contents=prompt
                )

                results = self._parse_json_response(response.text)
                if not results:
                    logger.error(f"批次解析失败，{len(influencers)} 位候选人未评分")
                    return False

                updated = 0
                for res in results:
                    res = self._validate_score(res)
                    idx = res.get('id')
                    if idx is not None and 0 <= idx < len(influencers):
                        target = influencers[idx]
                        target.fit_score = res.get('fit_score')
                        target.fit_reason = res.get('fit_reason')
                        target.price_min = res.get('price_min')
                        target.price_max = res.get('price_max')
                        updated += 1

                logger.info(f"批次评分完成: {updated}/{len(influencers)} 更新成功")
                return True

            except Exception as e:
                logger.error(f"Analyst 批量评估失败: {e}")
                return False

    async def run(self, brand_requirement: str, budget_range: tuple = None):
        with get_db() as db:
            pending_list = db.query(Influencer).filter(Influencer.fit_score == None).all()
            if not pending_list:
                logger.info("没有待评分的候选人")
                return

            logger.info(f"开始评分: {len(pending_list)} 位候选人")

            batches = [pending_list[i:i + BATCH_SIZE] for i in range(0, len(pending_list), BATCH_SIZE)]
            tasks = [self.analyze_batch(brand_requirement, batch, budget_range) for batch in batches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 记录失败的 batch
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch {i} 异常: {result}")
                elif not result:
                    logger.warning(f"Batch {i} 评分失败")

            db.commit()
            logger.info("Analyst 评分全部完成")
