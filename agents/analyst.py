import os
import asyncio
import json
import re
from google import genai
from database import get_db, Influencer
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


class AnalystAgent:
    def __init__(self):
        self.db = get_db()

    async def analyze_batch(self, brand_requirement, influencers):
        """
        批量评估：结合真实粉丝数进行定价
        """
        inf_list_text = ""
        for i, inf in enumerate(influencers):
            # 这里的 follower_count 是 Scout 查出来的真实数据
            inf_list_text += f"ID: {i} | 名称: {inf.name} | 粉丝数: {inf.follower_count} | 简介: {inf.tags[:150]}\n"

        prompt = f"""
        你是一个资深的海外营销专家。品牌需求：'{brand_requirement}'

        待评估博主列表：
        {inf_list_text}

        任务：
        1. Fit Score: 1-100 评分（考虑粉丝量与需求的匹配度）。
        2. Price Range: 预测单条视频合作价格(USD)。
           - 参考：YouTube 价格通常为 粉丝数 * $0.02 到 $0.05。
           - 如果是极精准的垂类博主，溢价 20-50%。
           - 如果粉丝数过万但简介不相关，价格下调。

        请严格以 JSON 数组输出，不要有额外文字：
        [
          {{"id": 0, "fit_score": 85, "fit_reason": "理由...", "price_min": 500, "price_max": 1200}},
          ...
        ]
        """

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt
            )

            match = re.search(r'\[.*\]', response.text, re.DOTALL)
            if match:
                results = json.loads(match.group(0))
                for res in results:
                    idx = res.get('id')
                    if idx is not None and idx < len(influencers):
                        target = influencers[idx]
                        target.fit_score = res.get('fit_score')
                        target.fit_reason = res.get('fit_reason')
                        target.price_min = res.get('price_min')
                        target.price_max = res.get('price_max')
                return True
        except Exception as e:
            print(f"  ❌ Analyst 批量评估失败: {e}")
            return False

    async def run(self, brand_requirement):
        # 找出库中还没评分的博主
        pending_list = self.db.query(Influencer).filter(Influencer.fit_score == None).all()
        if not pending_list:
            return

        batch_size = 5
        batches = [pending_list[i:i + batch_size] for i in range(0, len(pending_list), batch_size)]

        tasks = [self.analyze_batch(brand_requirement, batch) for batch in batches]
        await asyncio.gather(*tasks)
        self.db.commit()