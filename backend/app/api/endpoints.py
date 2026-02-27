from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models import User, ChatSession, ChatMessage, ClaimCheck, VerdictEnum, LawArticleRevision, ExplanationCache, LawArticle, Law
from app.schemas import LoginPayload, UserResponse, CheckRequest
from app.core.database import get_db
from app.services.rag_service import LegalFactChecker
from app.services.hook_service import InputAnalyzer, OutputValidator
from app.services.agent_service import RoutingAgent
from app.services.vision_service import VisionAnalyzer
from app.plugins.precedent_search import search_precedents
from app.plugins.calculator import calculate_dismissal_notice_allowance, calculate_severance_pay
import json

router = APIRouter()
checker = LegalFactChecker()
analyzer = InputAnalyzer()
agent = RoutingAgent()
validator = OutputValidator()
vision = VisionAnalyzer()

@router.get("/")
def read_root():
    return {"status": "ok", "message": "Legal Fact Checker API is running"}

@router.get("/debug/docx")
def debug_docx():
    import os
    try:
        files = os.listdir("/home/sssssmmm/legalcheck/")
        return {"files": [f for f in files if "docx" in f.lower() or "pdf" in f.lower() or "api" in f.lower()]}
    except Exception as e:
        return {"error": str(e)}

@router.get("/search/articles")
def search_articles(query: str = Query(..., description="검색할 키워드"), db: Session = Depends(get_db)):
    """조문 키워드 검색 API (실시간 API 연동 하이브리드)"""
    from app.plugins.law_db import search_law_articles
    
    # 1. 실시간 데이터포털 API를 통해 먼저 상위 법령(예: '주택', '근로기준법')으로 검색 시도
    api_results = search_law_articles(law_name=query, keyword="", limit=10)
    
    results = []
    
    # API 호출 실패로 발생한 에러 메시지(결과값이 1개이고 조문번호가 '-')인지 검증
    # 만일 에러 메시지일 경우 무시하고 로컬 DB로 넘어감
    is_api_error = False
    if len(api_results) == 1 and api_results[0].get("조문번호") == "-":
        is_api_error = True

    if api_results and not is_api_error:
        for idx, res in enumerate(api_results):
            # 조문제목과 내용을 합쳐서 프론트엔드 파싱 규격에 맞게 변환
            content_preview = f"[{res['조문제목']}] {res['조문내용']}"
            if len(content_preview) > 500:
                content_preview = content_preview[:500] + "..."
                
            results.append({
                "law_name": res["법령명"],
                "article_number": res["조문번호"],
                "content": content_preview,
                "revision_id": f"api_{idx}"
            })
    else:
        # 2. 결과가 없거나(법령명 매칭 실패), 연동 오류일 경우 로컬 DB 전문검색으로 Fallback
        revisions = db.query(LawArticleRevision).filter(LawArticleRevision.content.ilike(f"%{query}%")).limit(10).all()
        for rev in revisions:
            article = db.query(LawArticle).filter(LawArticle.id == rev.article_id).first()
            law = db.query(Law).filter(Law.id == article.law_id).first() if article else None
            results.append({
                "law_name": law.name if law else "Unknown",
                "article_number": article.article_number if article else "Unknown",
                "content": rev.content[:200] + "...", # Preview
                "revision_id": rev.id
            })
            
    return {"results": results}

@router.post("/auth/login", response_model=UserResponse)
def login(payload: LoginPayload, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        user = User(
            email=payload.email,
            name=payload.name,
            provider=payload.provider,
            provider_id=payload.provider_id,
            image_url=payload.image_url
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@router.post("/check")
async def check_fact(request: CheckRequest, user_id: int, db: Session = Depends(get_db)):
    # Validate user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    session_id = request.session_id
    if not session_id:
        chat_session = ChatSession(user_id=user_id, title=request.query[:50])
        db.add(chat_session)
        db.commit()
        db.refresh(chat_session)
        session_id = chat_session.id
    else:
        chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not chat_session or chat_session.user_id != user_id:
            raise HTTPException(status_code=403, detail="Invalid session")

    # Load history
    messages = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at).all()
    history = [{"role": msg.role, "content": msg.content} for msg in messages]

    # Add user message to DB
    user_msg = ChatMessage(session_id=session_id, role="user", content=request.query)
    db.add(user_msg)
    db.commit()

    # 1. Input Hook: Analyze query intent
    intent_analysis = await analyzer.analyze_query(request.query)
    
    # 2. Agent: Decide necessary actions based on intent
    agent_decision = await agent.decide_action(intent_analysis)

    plugin_context = ""
    # 2.5 Process Image if provided (Vision API)
    if getattr(request, "image_data", None):
        vision_result = await vision.extract_text_from_image(request.image_data)
        plugin_context += "\n[사용자 첨부 이미지 분석 결과 (Vision AI)]\n" + vision_result + "\n"
        search_query += " " + vision_result[:200] # Use part of the image text for semantic search constraints

    # 3. Add keywords to query if it's a legal question
    if intent_analysis.get("is_legal_question") and intent_analysis.get("keywords"):
        search_query += " " + " ".join(intent_analysis["keywords"])

    # 4. Execute plugins based on agent decision
    if agent_decision.get("requires_precedent_search") and intent_analysis.get("keywords"):
        precedents = search_precedents(intent_analysis["keywords"])
        plugin_context += "\n[관련 판례/재결례 정보]\n" + json.dumps(precedents, ensure_ascii=False) + "\n"

    if agent_decision.get("requires_calculator"):
        # Very naive implementation for demonstration: extracting a hardcoded salary if we could, 
        # but here we just append the calculation logic directly so the LLM can use the formulas or references 
        # For a full implementation, we'd use LLM to extract salary/days from `request.query` first.
        plugin_context += "\n[수당 계산기 참고 정보]\n해고예고수당: 월급 ÷ 209 × 8 × 30\n퇴직금: (월급 × 3 ÷ 90) × 30 × (근무일수 ÷ 365)\n사용자가 명시한 금액이 있다면 위 공식으로 검증하세요.\n"

    # 5. Get RAG response using the enriched query
    result = await checker.check_fact_with_history(
        query=search_query, 
        chat_history=history, 
        plugin_context=plugin_context
    )
    
    raw_parsed_result = result["result"]
    verdict_str = raw_parsed_result.get("verdict", "ERROR").upper()
    
    # 6. Output Hook: Validate and Correct
    parsed_result = await validator.validate_and_correct(raw_parsed_result)
    
    # Map the new 5-step fields to variables (using the SAFE corrected result)
    summary_str = parsed_result.get("section_1_summary", "")
    explanation = parsed_result.get("section_2_law_explanation", "")
    example_case = parsed_result.get("section_3_real_case_example", "")
    caution_note = parsed_result.get("section_4_caution", "")
    counseling = parsed_result.get("section_5_counseling_recommendation", "")
    
    sources = result.get("sources", [])
    
    # Check for caching if we have revision_ids from the retrieval
    revision_ids = result.get("revision_ids", [])
    primary_revision_id = int(revision_ids[0]) if revision_ids else None
    
    if primary_revision_id:
        cache = db.query(ExplanationCache).filter(ExplanationCache.article_revision_id == primary_revision_id).first()
        if cache:
            pass # TODO: handle caching with new schema later
        else:
            # Save new high-quality explanation to cache
            new_cache = ExplanationCache(
                article_revision_id=primary_revision_id,
                plain_summary=explanation,
                example_case=example_case,
                caution_note=caution_note
            )
            db.add(new_cache)
            # We don't commit immediately, it'll be committed with the rest

    # Map string verdict to Enum
    if "일부 사실" in verdict_str or "PARTIAL" in verdict_str:
        verdict_enum = VerdictEnum.PARTIAL
    elif "사실 아님" in verdict_str or "FALSE" in verdict_str:
        verdict_enum = VerdictEnum.FALSE
    elif "사실" in verdict_str or "TRUE" in verdict_str:
        verdict_enum = VerdictEnum.TRUE
    else:
        verdict_enum = VerdictEnum.PARTIAL # Defaulting on error

    # Save ClaimCheck record
    claim_check = ClaimCheck(
        claim_text=request.query,
        verdict=verdict_enum,
        explanation=explanation
    )
    db.add(claim_check)
    
    # We could link the revision here if our retriever returned the revision IDs.
    if primary_revision_id:
        rev_obj = db.query(LawArticleRevision).filter(LawArticleRevision.id == primary_revision_id).first()
        if rev_obj:
            claim_check.revisions.append(rev_obj)
    
    # Add AI message to DB (storing as JSON string for now)
    ai_msg = ChatMessage(session_id=session_id, role="ai", content=json.dumps(parsed_result, ensure_ascii=False))
    db.add(ai_msg)
    db.commit()

    return {
        "session_id": session_id,
        "result": parsed_result,
        "sources": sources,
        "intent_analysis": intent_analysis,
        "agent_decision": agent_decision
    }
