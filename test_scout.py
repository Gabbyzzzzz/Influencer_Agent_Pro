import asyncio
from agents.scout import ScoutAgent


async def main():
    test_requirement = "寻找 YouTube 上关注高龄宠物护理的博主。"
    scout = ScoutAgent()

    # 使用 await 启动异步任务
    await scout.run(test_requirement)


if __name__ == "__main__":
    asyncio.run(main())