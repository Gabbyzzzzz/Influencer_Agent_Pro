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
        """Multi-layer fallback JSON parsing."""
        # Attempt 1: Direct parse
        try:
            result = json.loads(text)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

        # Attempt 2: Extract from markdown code block
        m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if m:
            try:
                result = json.loads(m.group(1))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # Attempt 3: Regex match first JSON array
        m = re.search(r'\[[\s\S]*?\](?=\s*$|\s*[^,\]\}])', text)
        if m:
            try:
                result = json.loads(m.group(0))
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        logger.warning(f"All JSON parse attempts failed, raw response: {text[:300]}...")
        return []

    def _validate_score(self, res: dict) -> dict:
        """Validate and correct AI scoring output."""
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
            verified_tag = "verified" if inf.followers_verified else "unverified"
            inf_list_text += (
                f"ID: {i} | Name: {inf.name} | Platform: {inf.platform} | "
                f"Followers: {inf.follower_count:,} ({verified_tag}) | Bio: {snippet}\n"
            )

        budget_hint = ""
        if budget_range:
            budget_hint = f"""
Brand budget range: ${budget_range[0]:,} - ${budget_range[1]:,} USD per collaboration.
IMPORTANT: Use budget to inform scoring:
- Influencers whose estimated price fits within budget should get a BONUS (+5-10 points)
- Influencers way above budget (>3x) should be penalized (-10-15 points) in fit_score
- Still include all influencers but clearly note budget fit in the reason
"""

        prompt = f"""You are a senior influencer marketing strategist. Evaluate these candidates.

Brand requirement: '{brand_requirement}'
{budget_hint}
Candidates:
{inf_list_text}

Tasks:
1. **Fit Score (1-100)**: Rate brand fit considering:
   - Content relevance to the brand requirement (most important, 40% weight)
   - Follower count and audience size (20% weight)
   - Platform suitability for the brand (20% weight)
   - Budget fit if budget is specified (20% weight)
   - Be STRICT: generic/irrelevant creators should score below 30
   - Only truly relevant niche creators should score above 70

2. **Price Range (USD)**: Estimate per-collaboration cost:
   Pricing tiers by follower count:
   - Nano (<10K): $50-$200 (fixed)
   - Micro (10K-100K): followers × $0.02-$0.05
   - Mid (100K-500K): followers × $0.05-$0.08
   - Macro (500K+): followers × $0.08-$0.12

   Platform multipliers:
   - YouTube: ×1.0 (baseline)
   - Instagram: ×0.6
   - TikTok: ×0.4 (high engagement: ×0.6-0.8)

   Premiums: niche specialist +20-50%, high engagement +10-30%
   If followers = 0 and unverified: set price_min=0, price_max=0

3. **Fit Reason**: Brief explanation (English, under 60 chars) of why this creator fits or doesn't.

Output format (strict JSON array, no extra text):
[
  {{"id": 0, "fit_score": 85, "fit_reason": "Pet memorial niche, strong audience alignment", "price_min": 500, "price_max": 1200}},
  {{"id": 1, "fit_score": 25, "fit_reason": "Gaming content, no brand relevance", "price_min": 50, "price_max": 100}}
]"""

        async with self.semaphore:
            try:
                response = await asyncio.to_thread(
                    _get_client().models.generate_content,
                    model="gemini-2.0-flash",
                    contents=prompt
                )

                results = self._parse_json_response(response.text)
                if not results:
                    logger.error(f"Batch parse failed, {len(influencers)} candidates unscored")
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

                logger.info(f"Batch scoring complete: {updated}/{len(influencers)} updated")
                return True

            except Exception as e:
                logger.error(f"Analyst batch evaluation failed: {e}")
                return False

    async def run(self, brand_requirement: str, budget_range: tuple = None):
        with get_db() as db:
            pending_list = db.query(Influencer).filter(Influencer.fit_score == None).all()
            if not pending_list:
                logger.info("No candidates pending scoring")
                return

            logger.info(f"Scoring {len(pending_list)} candidates")

            batches = [pending_list[i:i + BATCH_SIZE] for i in range(0, len(pending_list), BATCH_SIZE)]
            tasks = [self.analyze_batch(brand_requirement, batch, budget_range) for batch in batches]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Batch {i} exception: {result}")
                elif not result:
                    logger.warning(f"Batch {i} scoring failed")

            db.commit()
            logger.info("Analyst scoring complete")
