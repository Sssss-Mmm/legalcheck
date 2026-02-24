from sqlalchemy import Column, Integer, String, Text, DateTime, Date, Boolean, ForeignKey, Enum, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

# PGVector 사용 시 아래 주석을 해제하세요.
# from pgvector.sqlalchemy import Vector

class VerdictEnum(enum.Enum):
    TRUE = "TRUE"
    PARTIAL = "PARTIAL"
    FALSE = "FALSE"

# 다대다 연결 테이블: LawArticle <-> Topic
article_topic_association = Table(
    "article_topic",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("law_articles.id"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True)
)

# 다대다 연결 테이블 (피드백 반영): ClaimCheck <-> LawArticleRevision
# 여러 조문을 근거로 하나의 사용자의 주장을 팩트체크할 수 있도록 설계
claim_revision_association = Table(
    "claim_revision",
    Base.metadata,
    Column("claim_id", Integer, ForeignKey("claim_checks.id"), primary_key=True),
    Column("revision_id", Integer, ForeignKey("law_article_revisions.id"), primary_key=True)
)

class Law(Base):
    """법률 기본 정보"""
    __tablename__ = "laws"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False) # 근로기준법
    short_name = Column(String(100), nullable=True)        # 근기법
    jurisdiction = Column(String(50), default="KR")        # 국가
    created_at = Column(DateTime, default=datetime.utcnow)

    articles = relationship("LawArticle", back_populates="law", cascade="all, delete-orphan")

class LawArticle(Base):
    """조문 기본 정보"""
    __tablename__ = "law_articles"

    id = Column(Integer, primary_key=True, index=True)
    law_id = Column(Integer, ForeignKey("laws.id"), nullable=False)
    article_number = Column(String(50), index=True, nullable=False) # 제36조
    title = Column(String(255), nullable=True)                      # 임금 지급
    is_active = Column(Boolean, default=True)                       # 현재 유효 여부

    law = relationship("Law", back_populates="articles")
    revisions = relationship("LawArticleRevision", back_populates="article", cascade="all, delete-orphan")
    topics = relationship("Topic", secondary=article_topic_association, back_populates="articles")

class LawArticleRevision(Base):
    """조문 개정 이력 관리 (핵심)"""
    __tablename__ = "law_article_revisions"

    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, ForeignKey("law_articles.id"), nullable=False)
    content = Column(Text, nullable=False)                           # 조문 원문
    effective_start_date = Column(Date, index=True, nullable=False)  # 시행 시작일
    effective_end_date = Column(Date, index=True, nullable=True)     # 시행 종료일
    summary_plain = Column(Text, nullable=True)                      # 쉬운 설명
    amendment_note = Column(Text, nullable=True)                     # 개정 이유
    
    # RAG 검색용 Vector DB 연동 (PostgreSQL + pgvector 사용 시)
    # embedding = Column(Vector(1536), nullable=True)

    article = relationship("LawArticle", back_populates="revisions")
    explanation_caches = relationship("ExplanationCache", back_populates="revision", cascade="all, delete-orphan")
    claim_checks = relationship("ClaimCheck", secondary=claim_revision_association, back_populates="revisions")

class Topic(Base):
    """주제 분류"""
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False) # 예: 임금체불
    description = Column(Text, nullable=True)

    articles = relationship("LawArticle", secondary=article_topic_association, back_populates="topics")

class ClaimCheck(Base):
    """팩트체크 기록"""
    __tablename__ = "claim_checks"

    id = Column(Integer, primary_key=True, index=True)
    claim_text = Column(Text, nullable=False)                       # 사용자 주장
    verdict = Column(Enum(VerdictEnum), index=True, nullable=False) # 판정 결과
    explanation = Column(Text, nullable=False)                      # 판정 이유
    created_at = Column(DateTime, default=datetime.utcnow)

    # 연결된 근거 조문들 (개정 이력 기준)
    revisions = relationship("LawArticleRevision", secondary=claim_revision_association, back_populates="claim_checks")

class ExplanationCache(Base):
    """LLM 설명 캐싱"""
    __tablename__ = "explanation_caches"

    id = Column(Integer, primary_key=True, index=True)
    article_revision_id = Column(Integer, ForeignKey("law_article_revisions.id"), nullable=False, unique=True)
    plain_summary = Column(Text, nullable=False) # 쉬운 설명
    example_case = Column(Text, nullable=True)   # 사례
    caution_note = Column(Text, nullable=True)   # 주의사항
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    revision = relationship("LawArticleRevision", back_populates="explanation_caches")
