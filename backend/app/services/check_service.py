"""
팩트체크 오케스트레이션 서비스
endpoints.py의 God Function(check_fact)에서 비즈니스 로직을 분리하여
HTTP 레이어와 비즈니스 로직의 관심사를 분리합니다.
"""
import json
import logging
from sqlalchemy.orm import Session
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from app.models import ChatSession, ChatMessage, ClaimCheck, LawArticleRevision, ExplanationCache
from app.core.llm import get_main_llm
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
        """
        CheckService 초기화 메서드.
        팩트체크 파이프라인의 각 단계에서 사용되는 서비스 객체들을 의존성 주입받습니다.
        """
        self.checker = checker
        self.analyzer = analyzer
        self.agent = agent
        self.validator = validator
        self.vision = vision

    def get_or_create_session(self, db: Session, user_id: int, session_id: int | None, query: str) -> tuple[int, ChatSession]:
        """
        사용자의 채팅 세션을 조회하거나, 세션이 없을 경우 새로 생성하여 반환합니다.

        Args:
            db (Session): 데이터베이스 세션
            user_id (int): 사용자 ID
            session_id (int | None): 기존 세션 ID (없으면 None)
            query (str): 채팅 세션의 제목으로 사용될 사용자 쿼리 질문

        Returns:
            tuple[int, ChatSession]: 생성 또는 조회된 세션 ID와 ChatSession 객체
        """
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
        """
        특정 세션 ID의 과거 채팅 내역을 조회하여 LLM이 처리하기 쉬운 딕셔너리 포맷 리스트로 반환합니다.

        Args:
            db (Session): 데이터베이스 세션
            session_id (int): 조회할 채팅 세션 ID

        Returns:
            list[dict]: "role" (user/ai)과 "content" 정보를 포함한 채팅 메시지 리스트
        """
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.created_at).all()
        return [{"role": msg.role, "content": msg.content} for msg in messages]

    async def build_plugin_context(self, query: str, intent_analysis: dict, agent_decision: dict, image_data: str | None = None) -> tuple[str, str]:
        """
        비전 API 분석, 사전 키워드 추출, 판례 검색 메타데이터, 계산기 공식 등 외부 플러그인의 결과물을 조합하여 
        LLM 판단의 정확도를 높이는 추가 문맥(Context)과 RAG 검색용 쿼리를 생성합니다.

        Args:
            query (str): 사용자의 원본 질문
            intent_analysis (dict): Input Hook에서 추출된 의도 분석 결과
            agent_decision (dict): Agent 단계에서 판단한 도구 사용 여부 및 목적
            image_data (str | None, optional): 참조 이미지 데이터 (Base64). Defaults to None.

        Returns:
            tuple[str, str]: 확장된 참고 문맥(plugin_context) 문자열 및 RAG 검색에 활용할 최종 질의어(search_query) 문자열
        """
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
        """
        전체 파이프라인의 결과물인 팩트체크 분석 내용을 데이터베이스에 기록하고,
        사용자와 AI 간의 채팅 메시지로 저장합니다.

        Args:
            db (Session): 데이터베이스 세션
            session_id (int): 현재 처리 중인 채팅 세션 ID
            query (str): 팩트체크 대상이 되는 사용자의 질문 (클레임)
            parsed_result (dict): Output Validator를 거쳐 교정된 최종 AI 답변 초안 딕셔너리
            result (dict): RAG 모듈 등 내부 처리 과정의 메타데이터(revision_ids 등)가 포함된 원형 데이터
        """
        raw_parsed_result = result["result"]
        verdict_str = raw_parsed_result.get("verdict", "ERROR").upper()

        # UNCLEAR (clarification) 응답은 근거 조문이 없으므로 단순 메시지만 저장
        if verdict_str == "UNCLEAR":
            ai_msg = ChatMessage(
                session_id=session_id,
                role="ai",
                content=json.dumps(parsed_result, ensure_ascii=False)
            )
            db.add(ai_msg)
            db.commit()
            return

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

    async def _generate_clarification_question(self, query: str, agent_decision: dict, history: list[dict]) -> dict:
        """
        사용자의 질문에 핵심적인 정보가 누락되어 검증을 진행할 수 없을 때, 이를 역으로 다시 물어보는
        질문 텍스트(Clarification Question)를 생성하여 반환합니다.
        
        Args:
            query (str): 정보가 누락된 사용자 질문
            agent_decision (dict): 추가 확인이 필요하다고 판단한 AI의 논리적 이유(reasoning)가 담긴 딕셔너리
            history (list[dict]): 사용자와의 이전 대화 내역

        Returns:
            dict: 팩트체크 결과 형식(verdict='UNCLEAR')으로 구성된 역질문 답변 딕셔너리
        """
        system_prompt = """당신은 법률 팩트체커 어시스턴트입니다.
사용자의 질문에 대답하기 위해 필수적인 정보(근로시간, 상시근로자 수 등)가 누락되어 팩트체크를 진행할 수 없습니다.
분석된 이유(reasoning)를 바탕으로, 사용자에게 필요한 정보를 자연스럽고 친절하게 되물어보는 질문을 1~2문장으로 작성하세요.

반드시 아래 JSON 형식으로 응답하세요:
{
    "verdict": "UNCLEAR",
    "section_2_law_explanation": "친절한 역질문 내용 작성",
    "section_3_real_case_example": "",
    "section_4_caution": ""
}"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("user", f"사용자 질문: {query}\n\n누락 정보 분석 사유: {agent_decision.get('reasoning')}\n\n이전 대화 맥락: {history}")
        ])
        
        llm = get_main_llm()
        chain = prompt | llm | JsonOutputParser()
        try:
            return await chain.ainvoke({})
        except Exception as e:
            logger.error(f"Clarification generation failed: {e}")
            return {
                "verdict": "UNCLEAR",
                "section_2_law_explanation": "사안을 판단하기 위해 추가적인 정보가 필요합니다. 당시 상황을 조금 더 자세히 설명해 주시겠어요?",
                "section_3_real_case_example": "",
                "section_4_caution": ""
            }

    async def execute(self, db: Session, user_id: int, query: str, session_id: int | None = None, image_data: str | None = None) -> dict:
        """
        단일 사용자의 팩트체크 요청을 처리하는 전체 파이프라인 로직을 관장하고 실행합니다.
        세션 생성, Intent 분석(Hook), 플러그인 도구 결정(Agent), RAG 검색 및 판정, 답변 교정(Output Hook), DB 기록 단계로 구성됩니다.

        Args:
            db (Session): 데이터베이스 세션
            user_id (int): 팩트체크를 요청한 사용자의 식별 ID
            query (str): 팩트체크 대상이 되는 질문 또는 주장문
            session_id (int | None, optional): 기존 채팅방의 세션 ID. 생성 시엔 None. Defaults to None.
            image_data (str | None, optional): 첨부된 이미지 데이터(Base64 문자열). Defaults to None.

        Returns:
            dict: 세션 ID, 최종 판정 결과, 참고 자료 출처 및 AI 파이프라인 로깅 데이터
        """
        # 1. 세션 관리
        session_id, chat_session = self.get_or_create_session(db, user_id, session_id, query)

        # 2. 히스토리 로드 & 사용자 메시지 저장
        history = self.load_chat_history(db, session_id)
        user_msg = ChatMessage(session_id=session_id, role="user", content=query)
        db.add(user_msg)
        db.commit()

        # 3. Input Hook & Agent
        intent_analysis = await self.analyzer.analyze_query(query)
        agent_decision = await self.agent.decide_action(intent_analysis, history)

        # 3.5 Clarification Branch (역질문이 필요한 경우 RAG 스킵)
        if agent_decision.get("requires_clarification"):
            clarification_result = await self._generate_clarification_question(query, agent_decision, history)
            clarification_result["is_clarification"] = True
            
            self.save_results(db, session_id, query, clarification_result, {
                "result": clarification_result,
                "revision_ids": []
            })
            
            return {
                "session_id": session_id,
                "result": clarification_result,
                "sources": [],
                "intent_analysis": intent_analysis,
                "agent_decision": agent_decision
            }

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
        parsed_result["is_clarification"] = False

        # 7. DB 저장
        self.save_results(db, session_id, query, parsed_result, result)

        return {
            "session_id": session_id,
            "result": parsed_result,
            "sources": result.get("sources", []),
            "intent_analysis": intent_analysis,
            "agent_decision": agent_decision
        }
