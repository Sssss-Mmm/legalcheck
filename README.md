# ⚖️ Legal Fact Checker (법률 팩트체커)

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?style=flat&logo=python&logoColor=white" alt="Python Badge"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI Badge"/>
  <img src="https://img.shields.io/badge/Next.js-000000?style=flat&logo=next.js&logoColor=white" alt="Next.js Badge"/>
  <img src="https://img.shields.io/badge/PostgreSQL-336791?style=flat&logo=postgresql&logoColor=white" alt="PostgreSQL Badge"/>
  <img src="https://img.shields.io/badge/ChromaDB-FF5722?style=flat" alt="ChromaDB Badge"/>
  <img src="https://img.shields.io/badge/OpenAI%20API-412991?style=flat&logo=openai&logoColor=white" alt="OpenAI Badge"/>
</div>
<br>

일반인이 근로기준법 등 생활 법률을 쉽게 이해하고 확인할 수 있도록 돕는 AI 기반 "법령 검증 및 팩트체크" 서비스입니다. 단순한 Q&A 챗봇을 넘어, 법률적 사실을 구조화하고 특정 시점의 개정 법령 및 판례를 바탕으로 판정하는 **팩트체크 엔진**을 목표로 합니다.

---

## ✨ 주요 기능 (Features)

### 1. ⚖️ 법령 및 판례 기반 팩트체크 엔진 (RAG 파이프라인)
- **사용자 주장 검증**: "회사가 월급을 2개월 안 줘도 된다"는 등의 주장을 입력하면 AI가 관련 법 조문과 판례를 검색하여 사실 여부를 판정합니다.
- **멀티턴 질의응답 (Multi-turn Chatbot)**: 팩트체크에 필수적인 정보가 누락된 경우, 사용자에게 구체적인 상황을 묻는 추가 질문을 통해 맥락을 파악하고 보다 정확한 판정을 내립니다.
- **판례 검색 통합 (Precedent Search)**: 단순 법조문을 넘어 실제 법원 판례 데이터를 참고하여 더욱 정확하고 현실적인 법적 해석을 제공합니다.
- **구조화된 판정 결과**: LLM이 일관된 형식(JSON)으로 답변을 반환합니다.
  - `TRUE`(사실), `PARTIAL`(일부 사실), `FALSE`(사실 아님) 판정 및 쉬운 설명 제공

### 2. 📝 AI 기반 법률 문서 초안 자동 생성 (Document Generation)
- **문서 자동 완성**: 팩트체크를 통해 검증된 사용자의 권리 침해 사실을 바탕으로 **내용증명, 노동청 진정서** 등의 법률 문서 초안을 자동 생성합니다.
- **쉬운 복사 및 활용**: 생성된 문서는 클립보드에 바로 복사하여 활용할 수 있습니다. (법적 보장 제외 사전 고지)

### 3. 👁️ 비전 AI 기반 문서 분석 (Vision API)
- **이미지 첨부 지원**: 질문 시 근로계약서, 임금명세서 등의 이미지를 첨부하면 비전 AI가 판독하여 사용자 상황에 맞춘 훨씬 구체적인 팩트체크를 진행합니다.

### 4. 🗄️ 체계적인 법률 데이터베이스 스키마
- **개정 이력 관리**: `LawArticleRevision` 및 `PostgreSQL`을 활용해 법률 개정 시점을 추적, 특정 시점 기준의 팩트체크를 견고하게 지원합니다.

### 5. 💻 사용자 친화적인 UX 및 대시보드 (Frontend)
- Next.js 기반 반응형 대시보드 및 NextAuth(Google OAuth) 소셜 로그인 연동.
- 과거 질문 이력을 저장하는 사이드바 히스토리 및 세션 북마크 기능.

---

## 🏗️ 시스템 아키텍처 (System Architecture)

```mermaid
graph TD
    User(["👨‍💻 사용자"]) -->|1. 팩트체크 요청 (+이미지, 판례 검색)| Frontend["Next.js Frontend"]
    User -->|2. 법률 문서 초안 생성 요청| Frontend
    Frontend -->|OAuth 인증| NextAuth["NextAuth.js"]
    Frontend -- REST API --> Backend["FastAPI Backend"]

    Admin(["👮 관리자"]) -->|법령 PDF 업로드| Backend

    subgraph Backend Services
        Backend --> Vision["👁️ Vision Service"]
        Backend --> RAG["🧠 RAG Service (법령 + 판례 검색)"]
        Backend --> Agent["🤖 Agent & Check Service"]
        Backend --> Template["📝 Template Service"]
        Backend --> DataParsing["📄 파싱 엔진"]
    end

    Vision -->|이미지 분석| LLM
    RAG <-->|유사도 문서 검색| VectorDB[("ChromaDB")]
    Agent -->|검증 및 생성| LLM["OpenAI API"]
    Template -->|문서 초안 생성| LLM
    
    DataParsing -->|법조문 구조화/단편화| DB[("PostgreSQL Database")]
    DataParsing -->|임베딩 저장| VectorDB

    Backend <-->|CRUD 및 캐싱| DB
```

---

## 💡 주요 기술 결정 및 트러블슈팅 (Key Decisions)

### 1. RAG(검색 증강 생성) 방식 채택 이유
> 일반적인 LLM 모델은 법률 용어나 사실관계에 있어 빈번한 환각(Hallucination) 현상을 보입니다. **정확한 팩트가 생명인 법률 서비스의 특성상**, 최신 판례와 명확한 법조문을 Vector Store(ChromaDB)에 임베딩하고 이를 기반으로만 답변을 강제하는 RAG 아키텍처를 도입하여 신뢰도를 대폭 높였습니다.

### 2. 복잡한 의존성 해결을 위한 Domain-Driven 설계 (DDD)
> 프로젝트가 확장되면서 서비스 로직이 한 곳에 뭉쳐 유지보수가 어려워지는 "God Function" 문제를 겪었습니다. 이를 해결하기 위해 백엔드를 **API Router / Core (설정) / Services (비즈니스 로직) / Plugins (외부 통신)** 패턴으로 분리하고 의존성 주입(Dependency Injection)을 도입하여 테스트의 용이성과 확장성을 확보했습니다.

### 3. 멀티턴(Multi-Turn) 꼬리 질문과 컨텍스트 유지
> 사용자가 처음부터 모든 법적 상황을 완벽히 설명하지 못하는 점을 고려해, AI 에이전트가 "팩트체크에 필수적인 정보"가 누락되었는지 먼저 판단하는 선행 검증 단계를 추가했습니다. 세션 기반으로 대화 맥락을 계속 저장하고 불러오면서 똑똑하고 원활한 멀티턴 로직을 구현했습니다.

---

## 📂 프로젝트 구조 (Repository Structure)

```text
legalcheck/
├── backend/                  # FastAPI 기반 백엔드 모듈
│   ├── app/api/              # REST 엔드포인트 라우터 관리
│   ├── app/services/         # RAG, 검증 로직, 문서 추출 등 핵심 비즈니스 로직
│   ├── app/models/           # PostgreSQL 테이블 스키마 정의 (SQLAlchemy)
│   ├── app/plugins/          # 판례 크롤링 등 외부 확장 기능 관리
│   └── chromadb/             # Vector Store 파일 마운트 공간
└── frontend/                 # Next.js (App Router) 기반 사용자 대시보드
    ├── src/app/              # 페이지 라우팅 로직 (채팅, 검색, 템플릿 등)
    └── src/components/       # UI/UX 모듈 및 재사용 React 컴포넌트
```

---

## 🚀 환경 설정 및 셋업 가이드 (Setup)

### 1. 필수 요구사항
- Python 3.11 이상 및 `uv` 패키지 관리자
- Node.js 18 이상
- Docker 및 Docker Compose
- OpenAI API Key 발급

### 2. 환경 변수 초기 세팅
1. 백엔드 : `backend/.env` 파일 생성 후 `OPENAI_API_KEY`, `POSTGRES_USER` 등 작성
2. 프론트엔드 : `frontend/.env.local` 파일 생성 후 구글 소셜 간편로그인을 위한 키 작성
   ```env
   NEXTAUTH_URL=http://localhost:3000
   GOOGLE_CLIENT_ID=여러분의_구글_클라이언트_아이디
   GOOGLE_CLIENT_SECRET=여러분의_구글_클라이언트_시크릿
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

### 3. 일괄 실행 (Docker Compose)
가장 권장하는 로컬 서버 실행 방식입니다. 최상위(`legalcheck/`) 경로에서 아래 시크립트를 실행하면 백엔드와 데이터베이스가 동시에 켜집니다.
```bash
docker-compose up -d --build
```
> **Tip:** WSL 환경에서 Permission denied 에러 발생 시 Docker Desktop 설정에서 WSL 연동 옵션을 켜주세요.

### 4. 프론트엔드 개별 실행
```bash
cd frontend
npm install
npm run dev
```

---

## 🤝 기여자 및 연락처 (Contact & License)
- **Maintainer**: 홍길동 ([email@example.com](mailto:email@example.com))
- 이 프로젝트는 [본인 깃허브 주소 링크](#)에서 지속적으로 개선 중입니다.
- 이 저장소는 라이선스 정책의 적용을 받습니다. (License: [MIT License](LICENSE))
