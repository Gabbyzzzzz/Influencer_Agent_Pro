import asyncio
from agents.scout import ScoutAgent
from agents.analyst import AnalystAgent


async def main():
    brand_req = "推广高端宠物骨灰盒，找 YouTube 上专业的宠物康养或临终关怀博主。"

    # 1. 侦察阶段
    scout = ScoutAgent()
    await scout.run(brand_req)

    # 2. 分析阶段
    analyst = AnalystAgent()
    await analyst.run(brand_req)

    print("\n--- 🕵️ Agent 执行结果预览 ---")
    from database import get_db, Influencer
    with get_db() as db:
        top_picks = db.query(Influencer).order_by(Influencer.fit_score.desc()).limit(3).all()

        for i, inf in enumerate(top_picks, 1):
            print(f"{i}. {inf.name}")
            score = inf.fit_score or "未评分"
            price = f"${inf.price_min:,.0f}-${inf.price_max:,.0f}" if inf.price_min else "未定价"
            reason = (inf.fit_reason or "无")[:100]
            print(f"   契合度: {score} | 预测价格: {price}")
            print(f"   理由: {reason}\n")


if __name__ == "__main__":
    asyncio.run(main())
