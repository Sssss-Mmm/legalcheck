import asyncio
from app.services.hook_service import InputAnalyzer

async def test():
    analyzer = InputAnalyzer()
    result = await analyzer.analyze_query("회사에서 갑자기 잘렸는데 돈도 안주고 너무 억울해요 ㅠㅠ 신고 가능?")
    print("Test Result:", result)

if __name__ == "__main__":
    asyncio.run(test())
