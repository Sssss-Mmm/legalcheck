import asyncio
from app.services.hook_service import InputAnalyzer
from app.services.agent_service import RoutingAgent
from app.plugins.precedent_search import search_precedents
import json

async def test():
    analyzer = InputAnalyzer()
    agent = RoutingAgent()
    
    questions = [
        "직장내 괴롭힘으로 짤린 사람들 판례 있어?",
        "해고예고수당 어떻게 계산해? 나 월급 200만원이야."
    ]
    
    for q in questions:
        print(f"\n--- [Test Query]: {q} ---")
        intent = await analyzer.analyze_query(q)
        decision = await agent.decide_action(intent)
        
        print("Agent Decision:", decision)
        
        plugin_context = ""
        if decision.get("requires_precedent_search") and intent.get("keywords"):
            precedents = search_precedents(intent["keywords"])
            plugin_context += "\n[관련 판례/재결례 정보]\n" + json.dumps(precedents, ensure_ascii=False) + "\n"
            
        if decision.get("requires_calculator"):
            plugin_context += "\n[수당 계산기 참고 정보]\n해고예고수당: 월급 ÷ 209 × 8 × 30\n"
            
        print("Generated Plugin Context:", plugin_context)

if __name__ == "__main__":
    asyncio.run(test())
