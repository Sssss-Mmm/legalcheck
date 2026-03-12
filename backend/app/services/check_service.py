"""
팩트체크 오케스트레이션 서비스
endpoints.py의 God Function(check_fact)에서 비즈니스 로직을 분리하여
HTTP 레이어와 비즈니스 로직의 관심사를 분리합니다.
"""
import json
import logging
from sqlalchemy.orm import Session

from app.models import ChatSession, ChatMessage, ClaimCheck, LawArticleRevision, ExplanationCache
from app.services.rag_service import LegalFactChecker
from app.services.hook_service import InputAnalyzer, OutputValidator
from app.services.agent_service import RoutingAgent
from app.services.vision_service import VisionAnalyzer
from app.services.verdict_utils import parse_verdict
from app.plugins.precedent_search import search_precedents

logger = logging.getLogger(__name__)


class CheckService:
    """팩트체크 요청의 전체 파이프라인을 관리하는 서비스"""

    def __init__(
        self,
        checker: LegalFactChecker,
        analyzer: InputAnalyzer,
        agent: RoutingAgent,
        validator: OutputValidator,
        vision: VisionAnalyzer,
    ):
        self.checker = checker
        self.analyzer = analyzer
        self.agent = agent
        self.validator = validator
        self.vision = vision

    def get_or_create_session(self, db: Session, user_id: int, session_id: int | None, query: str) -> tuple[int, ChatSession]:
        """세션을 가져오거나 새로 생성합니다."""
        if not session_id:
            chat_session = ChatSession(user_id=user_id, title=query[:50])
            db.add(chat_session)
            db.commit()
            db.refresh(chat_session)
            return chat_session.id, chat_session
        else:
            chat_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            return session_id, chat_session

    def load_chat_history(self, db: Session, session_id: int) -> list[dict]:
        """채팅 히스토리를 로드합니다."""
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def build_plugin_context(self, query: str, intent_analysis: dict, agent_decision: dict, image_data: str | None = None) -> tuple[str, str]:
        """플러그인 컨텍스트와 확장된 검색 쿼리를 빌드합니다."""
        plugin_context = ""
        search_query = query

        # Vision API
        if image_data:
            vision_result = await self.vision.extract_text_from_image(image_data)
            plugin_context += "\n[사용자 첨부 이미지 분석 결과 (Vision AI)]\n" + vision_result + "\n"
            search_query += " " + vision_result[:200]

        # Keyword 보강
        if intent_analysis.get("is_legal_question") and intent_analysis.get("keywords"):
            search_query += " " + " ".join(intent_analysis["keywords"])

        # 판례 검색
        if agent_decision.get("requires_precedent_search") and intent_analysis.get("keywords"):
            precedents = search_precedents(intent_analysis["keywords"])
            plugin_context += "\n[관련 판례/재결례 정보]\n" + json.dumps(precedents, ensure_ascii=False) + "\n"

        # 수당 계산기
        if agent_decision.get("requires_calculator"):
            plugin_context += (
                "\n[수당 계산기 참고 정보]\n"
                "해고예고수당: 월급 ÷ 209 × 8 × 30\n"
                "퇴직금: (월급 × 3 ÷ 90) × 30 × (근무일수 ÷ 365)\n"
                "사용자가 명시한 금액이 있다면 위 공식으로 검증하세요.\n"
            )

        return plugin_context, search_query

    def save_results(
        self,
        db: Session,
        session_id: int,
        query: str,
        parsed_result: dict,
        result: dict,
    ) -> None:
        """팩트체크 결과를 DB에 저장합니다."""
        raw_parsed_result = result["result"]
        verdict_str = raw_parsed_result.get("verdict", "ERROR").upper()

        # ExplanationCache
        revision_ids = [rid for rid in result.get("revision_ids", []) if rid is not None]
        primary_revision_id = int(revision_ids[0]) if revision_ids else None

        explanation = parsed_result.get("section_2_law_explanation", "")
        example_case = parsed_result.get("section_3_real_case_example", "")
        caution_note = parsed_result.get("section_4_caution", "")

        if primary_revision_id:
            cache = db.query(ExplanationCache).filter(
                ExplanationCache.article_revision_id == primary_revision_id
            ).first()
            if not cache:
                new_cache = ExplanationCache(
                    article_revision_id=primary_revision_id,
                    plain_summary=explanation,
                    example_case=example_case,
                    caution_note=caution_note
                )
                db.add(new_cache)

        # ClaimCheck
        verdict_enum = parse_verdict(verdict_str)
        claim_check = ClaimCheck(
            claim_text=query,
            verdict=verdict_enum,
            explanation=explanation
        )
        db.add(claim_check)

        if primary_revision_id:
            rev_obj = db.query(LawArticleRevision).filter(
                LawArticleRevision.id == primary_revision_id
            ).first()
            if rev_obj:
                claim_check.revisions.append(rev_obj)

        # AI 메시지 저장
        ai_msg = ChatMessage(
            session_id=session_id,
            role="ai",
            content=json.dumps(parsed_result, ensure_ascii=False)
        )
        db.add(ai_msg)
        db.commit()

    async def execute(self, db: Session, user_id: int, query: str, session_id: int | None = None, image_data: str | None = None) -> dict:
        """전체 팩트체크 파이프라인을 실행합니다."""
        # 1. 세션 관리
        session_id, chat_session = self.get_or_create_session(db, user_id, session_id, query)

        # 2. 히스토리 로드 & 사용자 메시지 저장
        history = self.load_chat_history(db, session_id)
        user_msg = ChatMessage(session_id=session_id, role="user", content=query)
        db.add(user_msg)
        db.commit()

        # 3. Input Hook & Agent
        intent_analysis = await self.analyzer.analyze_query(query)
        agent_decision = await self.agent.decide_action(intent_analysis)

        # 4. 플러그인 컨텍스트 빌드
        plugin_context, search_query = await self.build_plugin_context(
            query, intent_analysis, agent_decision, image_data
        )

        # 5. RAG 팩트체크
        result = await self.checker.check_fact_with_history(
            query=search_query,
            chat_history=history,
            plugin_context=plugin_context
        )

        # 6. Output Hook
        raw_parsed_result = result["result"]
        parsed_result = await self.validator.validate_and_correct(raw_parsed_result)

        # 7. DB 저장
        self.save_results(db, session_id, query, parsed_result, result)

        return {
            "session_id": session_id,
            "result": parsed_result,
            "sources": result.get("sources", []),
            "intent_analysis": intent_analysis,
            "agent_decision": agent_decision
        }
