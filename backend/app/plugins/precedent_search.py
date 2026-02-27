def search_precedents(keywords: list[str]) -> list[dict]:
    """
    판례 또는 노동위원회 재결례를 검색하는 플러그인 (현재는 Mock 데이터 반영)
    추후 Open API 또는 Vector DB에서 가져오도록 확장.
    """
    
    # Mocking a response for demonstration
    mock_db = {
        "부당해고": [
            {
                "case_number": "대법원 2012다14618",
                "summary": "서면통지 의무를 위반한 해고는 그 사유를 묻지 않고 무효이다. 이메일이나 문자메시지로만 통보한 해고도 효력이 없음을 명시한 판례."
            },
            {
                "case_number": "중앙노동위원회 2021부해490",
                "summary": "수습기간 중이라 하더라도 객관적이고 합리적인 평가 근거 없이 본채용을 거부하는 것은 부당해고에 해당한다."
            }
        ],
        "임금체불": [
            {
                "case_number": "대법원 2018도15783",
                "summary": "퇴직 후 14일 이내에 지급하지 않은 임금 및 퇴직금에 대하여, 사업주의 고의성이 인정되어 근로기준법 위반으로 처벌받은 사례."
            }
        ]
    }
    
    results = []
    
    for kw in keywords:
        for key, value in mock_db.items():
            if kw in key or key in kw:
                results.extend(value)
                break
                
    # 중복 제거
    unique_cases = {r["case_number"]: r for r in results}.values()
    
    if not unique_cases:
        return [{"case_number": "검색 결과 없음", "summary": f"입력하신 키워드({', '.join(keywords)})와 일치하는 주요 판례를 찾지 못했습니다. 관련 조문을 위주로 확인하시기 바랍니다."}]
        
    return list(unique_cases)
