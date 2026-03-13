# Legal Fact Checker (법률 팩트체커)

일반인이 근로기준법 등 생활 법률을 쉽게 이해하고 확인할 수 있도록 돕는 AI 기반 "법령 검증 및 팩트체크" 서비스입니다. 단순한 Q&A 챗봇을 넘어, 법률적 사실을 구조화하고 특정 시점의 개정 법령을 바탕으로 판정하는 **팩트체크 엔진**을 목표로 합니다.

---

## ✨ 주요 기능 (Features)

### 1. ⚖️ 법령 기반 팩트체크 엔진 (RAG 파이프라인)
- **사용자 주장 검증**: "회사가 월급을 2개월 안 줘도 된다"는 등의 주장을 입력하면 AI가 관련 법 조문을 검색하여 사실 여부를 판정합니다.
- **구조화된 판정 결과**: LLM이 줄글이 아닌 일관된 형식(JSON)으로 답변을 반환합니다.
  - **판정 (Verdict)**: `TRUE`(사실), `PARTIAL`(일부 사실), `FALSE`(사실 아님)
  - **쉬운 설명 (Explanation)**: 근거 조항(예: 근로기준법 제36조)과 함께 일반인의 눈높이에 맞춘 해석
  - **현실 적용 사례 (Example)**: 이해하기 쉬운 구체적인 예시 제공
  - **주의사항 (Caution)**: 예외 조건이나 판례상 달라질 수 있는 부분 안내

### 2. 📝 AI 기반 법률 문서 초안 자동 생성 (Document Generation)
- **문서 자동 완성**: 팩트체크를 통해 검증된 사용자의 권리 침해 사실을 바탕으로 **내용증명, 노동청 진정서** 등의 법률 문서 초안을 자동 생성합니다.
- **쉬운 복사 및 활용**: 생성된 문서는 클립보드에 바로 복사하여 실제 신고나 발송에 활용할 수 있습니다. (※ 법적 효력을 보장하지 않으므로 전문가 검토 권장 안내 포함)

### 3. 👁️ 비전 AI 기반 문서 분석 (Vision API)
- **이미지 첨부 지원**: 질문 시 근로계약서, 임금명세서 등의 이미지 파일을 첨부하면 비전 AI가 문서를 판독합니다.
- **맥락 인식 검증**: 추출된 문서의 내용을 바탕으로 사용자 상황에 훨씬 더 정확하고 구체화된 팩트체크 정보를 제공합니다.

### 4. 🗄️ 체계적인 법률 데이터베이스 스키마
법률 서비스에 필수적인 **개정 이력 관리**와 **캐싱**을 지원하도록 데이터베이스가 설계되었습니다.
- **`Law` & `LawArticle`**: 기본 법령과 조문 정보 (예: 근로기준법 제36조)
- **`LawArticleRevision` (개정 이력)**: 법률 개정 시점(`effective_start_date`, `end_date`)을 추적하여, 과거 특정 시점 기준의 팩트체크를 지원
- **`Topic`**: 조문별 태그(예: 임금체불, 퇴직금) 매핑을 통한 주제별 탐색 기능
- **`ClaimCheck`**: 사용자의 팩트체크 질문과 판정 결과를 DB에 기록하여 추후 오답 노트 및 파인튜닝 데이터로 활용
- **`ExplanationCache`**: LLM의 답변 비용 절감을 위한 "쉬운 설명" 캐싱 기능

### 5. 📄 관리자용 PDF 자동 법령 파싱 API (Admin)
- 관리자가 법령 원문 PDF 파일을 업로드하면, 백엔드 시스템이 텍스트를 파싱(PyPDFLoader)합니다.
- LLM을 활용해 문서에서 "제N조(제목)" 형태를 자동으로 인식하고 분리하여 데이터베이스에 자동 적재합니다.

### 6. 💻 사용자 친화적인 UX 및 대시보드 (Frontend)
- Next.js 기반의 반응형 팩트체크 대시보드
- Google OAuth 소셜 로그인 연동 (NextAuth)
- **직관적인 결과 UI**: 팩트체크 판정에 따른 색상별 뱃지(TRUE/PARTIAL/FALSE) 및 요약/해석/사례 분리형 카드 레이아웃 제공
- **사이드바 히스토리 및 북마크**: 과거 질문 및 검증 세션 기록을 손쉽게 확인하고, 중요한 세션은 북마크하여 별도 관리 가능
- **실시간 인기 팩트체크 추천**: 처음 방문한 사용자도 쉽게 질문해볼 수 있도록 안내
- **스마트 후속 질문 추천**: AI 답변 완료 후, 현재 대화 맥락에 맞는 예상 질문을 자동으로 제안하여 심도 있는 법률 탐색 지원
- **결과 원클릭 공유**: 검증된 팩트체크 결과를 타인과 빠르고 깔끔하게 공유할 수 있는 복사 기능

---

## 🏗️ 시스템 아키텍처 (System Architecture)

```mermaid
graph TD
    User([👨‍💻 사용자]) -->|1. 팩트체크 요청 (+이미지)| Frontend[Next.js Frontend]
    User -->|2. 법률 문서 초안 생성 요청| Frontend
    Frontend -->|OAuth 인증| NextAuth[NextAuth.js]
    Frontend -- REST API --> Backend[FastAPI Backend]

    Admin([👮 관리자]) -->|법령 PDF 업로드| Backend

    subgraph Backend Services
        Backend --> Vision[👁️ Vision Service]
        Backend --> RAG[🧠 RAG Service]
        Backend --> Agent[🤖 Agent & Check Service]
        Backend --> Template[📝 Template Service]
        Backend --> DataParsing[📄 파싱 엔진]
    end

    Vision -->|이미지 분석| LLM
    RAG <-->|유사도 문서 검색| VectorDB[(ChromaDB Vector Store)]
    Agent -->|검증 및 생성| LLM[OpenAI API<br>(gpt-4o / gpt-4o-mini)]
    Template -->|문서 초안 생성| LLM
    
    DataParsing -->|법조문 구조화/단편화| DB[(SQLite Database)]
    DataParsing -->|임베딩 저장| VectorDB

    Backend <-->|CRUD 및 캐싱| DB
    OpenData([🏛️ 공공데이터포털]) -.->|외부 API 통신| Backend
```

---

## 🛠️ 기술 스택 (Tech Stack)

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Architecture**: Domain-Driven Design (DDD) 기반 서비스 레이어 분리 (Service, Core, Plugins)
- **Database**: SQLite (향후 PostgreSQL + `pgvector` 전환 고려), SQLAlchemy (ORM), Alembic (Migration)
- **AI / RAG**: LangChain, OpenAI API (`gpt-4o`, `gpt-4o-mini`), ChromaDB (Vector Store)
- **Package Manager**: `uv`

### Frontend
- **Framework**: Next.js 15 (App Router), React 19
- **Styling**: Tailwind CSS
- **Authentication**: NextAuth.js (Google Provider)

---

## 🚀 설치 및 실행 방법 (Setup Guide)

### 1. 필수 요구사항
- Python 3.11 이상
- `uv` (Python 패키지 관리자)
- Node.js 18 이상
- OpenAI API Key

### 2. 백엔드 설정 (Backend)
```bash
cd backend

# 패키지 동기화 및 설치
uv sync

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 등의 환경변수를 입력하세요.

# 로컬 개발 서버 실행
uv run fastapi dev app/main.py
```

### 3. 프론트엔드 설정 (Frontend)
```bash
cd frontend

# 패키지 설치
npm install

# 환경변수 세팅
# .env.local 파일에 NEXTAUTH_URL, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET 등을 입력하세요.

# 개발 서버 실행
npm run dev
```

---

*이 프로젝트는 복잡한 법률 언어를 쉬운 일상어로 번역하고, "정확한 사실"만을 전달하기 위해 지속적으로 고도화되고 있습니다.*
