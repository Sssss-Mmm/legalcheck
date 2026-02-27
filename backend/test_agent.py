import asyncio
from app.services.hook_service import InputAnalyzer
from app.services.agent_service import RoutingAgent
import json

async def test():
    analyzer = InputAnalyzer()
    agent = RoutingAgent()
    
    questions = [
        "회사에서 갑자기 잘렸는데 돈도 안주고 너무 억울해요 ㅠㅠ 신고 가능?",
        "야간 수당 어떻게 계산해?",
        "직장내 괴롭힘으로 짤린 사람들 판례 있어?",
        "안녕 밥 먹었어?"
    ]
    
    for q in questions:
        print(f"\n--- Q: {q} ---")
        intent = await analyzer.analyze_query(q)
        print("Intent:", json.dumps(intent, ensure_ascii=False, indent=2))
        
        decision = await agent.decide_action(intent)
        print("Agent Decision:", json.dumps(decision, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
