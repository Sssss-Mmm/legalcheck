import asyncio
import json
from app.services.hook_service import OutputValidator

async def test():
    validator = OutputValidator()
    
    # 1. A bad draft with definitive outcomes and emotional language
    bad_draft = {
        "verdict": "사실",
        "section_1_summary": "100% 무조건 승소할 수 있습니다. 너무 걱정하지 마세요.",
        "section_2_law_explanation": "근로기준법 제26조에 따라 해고예고수당을 지급받지 못한 것은 명백한 위법입니다.",
        "section_3_real_case_example": "당신처럼 억울하게 잘린 사람들도 노동청에 신고해서 전원 돈을 다 받아냈습니다. 힘내세요!",
        "section_4_caution": "사장이 돈을 안 주면 배임죄로 무조건 감옥에 갑니다.",
        "section_5_counseling_recommendation": "혼자서도 충분히 이길 수 있으니 변호사는 필요 없습니다."
    }
    
    # 2. A good draft that should pass unchanged
    good_draft = {
        "verdict": "일부 사실",
        "section_1_summary": "상시 근로자 5인 미만 사업장의 경우 연차유급휴가 규정이 적용되지 않습니다.",
        "section_2_law_explanation": "근로기준법 제11조 및 제60조에 따르면, 상시 5명 이상의 근로자를 사용하는 사업장에만 연차휴가가 적용됩니다.",
        "section_3_real_case_example": "직원이 4명인 카페에서 1년을 일했더라도, 법적으로 연차휴가를 요구할 권리가 발생하지 않습니다.",
        "section_4_caution": "단, 사업주가 근로계약서에 연차휴가를 부여하겠다고 명시했다면 약정 휴가로서 청구할 수 있습니다.",
        "section_5_counseling_recommendation": "구체적인 상시 근로자 수 산정이나 계약서 해석에 이견이 있다면 노무사 등 전문가의 상담이 필요합니다."
    }
    
    print("=== [Test 1: Bad Draft (Emotional & Definitive)] ===")
    print(json.dumps(bad_draft, ensure_ascii=False, indent=2))
    
    safe_result1 = await validator.validate_and_correct(bad_draft)
    
    print("\n--- [Corrected Result] ---")
    print(json.dumps(safe_result1, ensure_ascii=False, indent=2))
    
    print("\n\n=== [Test 2: Good Draft (Normal)] ===")
    print(json.dumps(good_draft, ensure_ascii=False, indent=2))
    
    safe_result2 = await validator.validate_and_correct(good_draft)
    
    print("\n--- [Corrected Result (Should be mostly unchanged)] ---")
    print(json.dumps(safe_result2, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
