"""
PDF 법률 문서 파싱 서비스
admin.py에서 100줄 이상의 PDF 파싱 비즈니스 로직을 분리합니다.
"""
import os
import tempfile
import logging
from datetime import date

from sqlalchemy.orm import Session
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic import BaseModel, Field
from typing import List

from app.core.llm import get_mini_llm
from app.models import Law, LawArticle, LawArticleRevision

logger = logging.getLogger(__name__)


class ParsedArticle(BaseModel):
    article_number: str = Field(description="조문 번호. 예: 제36조")
    title: str = Field(description="조문 제목. 예: 임금 지급")
    content: str = Field(description="조문 내용 전체")


class ParsedLaw(BaseModel):
    articles: List[ParsedArticle] = Field(description="추출된 법 조문 목록")


class PDFLawParser:
    """PDF 파일에서 법 조문을 추출하고 DB에 삽입하는 서비스"""

    def __init__(self):
        """
        PDFLawParser의 생성자입니다.
        비용 및 속도 최적화를 위해 경량(Mini) LLM을 초기화하고,
        반환 형태를 ParsedLaw Pydantic 스키마에 맞춘 JSON 파서로 설정합니다.
        """
        self.llm = get_mini_llm()
        self.parser = JsonOutputParser(pydantic_object=ParsedLaw)

    def _load_pdf(self, file_content: bytes) -> str:
        """
        메모리상의 PDF 바이트(bytes) 데이터를 임시 파일로 저장한 뒤,
        PyPDFLoader를 이용해 내부의 모든 텍스트를 문자열로 추출하여 반환합니다.

        Args:
            file_content (bytes): 업로드된 PDF 원본 파일의 바이트 데이터

        Returns:
            str: PDF 문서에서 추출된 전체 텍스트
        """
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            loader = PyPDFLoader(tmp_path)
            documents = loader.load()
            return "\n".join([doc.page_content for doc in documents])
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def _parse_articles(self, text: str) -> list[dict]:
        """
        추출된 전체 법률 텍스트를 LLM에 전달하여,
        각 조항(조문 번호, 제목, 내용) 단위로 분해(Parsing)한 리스트를 반환합니다.

        Args:
            text (str): PDF에서 추출된 전체 텍스트 원문

        Returns:
            list[dict]: 각 조항 정보(article_number, title, content)가 담긴 딕셔너리 리스트
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 법률 문서 파싱 전문가입니다. 입력된 텍스트에서 각 조문(예: '제1조(목적) ...')을 분리하여 리스트 형태로 추출하세요."),
            ("user", "텍스트:\n{text}")
        ])

        chain = prompt | self.llm | self.parser
        # 안전한 텍스트 크기 제한 (LLM 컨텍스트 보호)
        from app.core.config import get_settings
        text_to_process = text[:get_settings().PDF_MAX_TEXT_LENGTH]
        return await chain.ainvoke({"text": text_to_process})

    def _save_articles(self, db: Session, law_id: int, articles_data: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        파싱 완료된 조문 데이터(딕셔너리)들을 RDBMS의 LawArticle 및 LawArticleRevision 테이블에 적재합니다.

        Args:
            db (Session): SQLAlchemy 데이터베이스 세션
            law_id (int): 해당 조문들이 속한 상위 법령(Law)의 기본키 ID
            articles_data (list[dict]): LLM이 파싱한 조항 정보 리스트

        Returns:
            tuple[list[dict], list[dict]]: DB에 삽입된 조문(Created Articles) 데이터 리스트와 벡터 DB 인덱싱을 위한 리비전(Embedded Revisions) 데이터 리스트의 튜플
        """
        created_articles = []
        embedded_revisions = []
        law = db.query(Law).filter(Law.id == law_id).first()

        for article_data in articles_data:
            db_article = LawArticle(
                law_id=law_id,
                article_number=article_data["article_number"],
                title=article_data["title"],
                is_active=True
            )
            db.add(db_article)
            db.flush()

            db_revision = LawArticleRevision(
                article_id=db_article.id,
                content=article_data["content"],
                effective_start_date=date.today(),
                effective_end_date=None
            )
            db.add(db_revision)
            db.flush()

            created_articles.append({
                "article_number": db_article.article_number,
                "title": db_article.title
            })

            embedded_revisions.append({
                "law_id": law_id,
                "article_id": db_article.id,
                "revision_id": db_revision.id,
                "content": db_revision.content,
                "law_name": law.name if law else "Unknown",
                "article_number": db_article.article_number
            })

        db.commit()
        return created_articles, embedded_revisions

    async def process_pdf(self, db: Session, law_id: int, file_content: bytes) -> tuple[list[dict], list[dict]]:
        """
        사용자가 업로드한 PDF 형식의 법률/시행령 문서를 처리하는 전체 파이프라인 메서드입니다.
        PDF 로드(텍스트 추출) → LLM 조문 파싱 → 관계형 DB(RDBMS) 저장 단계를 순차적으로 실행합니다.

        Args:
            db (Session): 데이터베이스 세션
            law_id (int): 대상 법령의 ID
            file_content (bytes): PDF 파일 원본 바이너리

        Returns:
            tuple[list[dict], list[dict]]: RDBMS에 생성된 조문 데이터 및 벡터 스토어 삽입용 추출 데이터 튜플
        """
        full_text = self._load_pdf(file_content)
        parsed_result = await self._parse_articles(full_text)
        articles_data = parsed_result.get("articles", [])
        return self._save_articles(db, law_id, articles_data)
