# Legal Fact Checker Backend

이 프로젝트는 **법률 팩트체커(Legal Fact Checker)** 서비스의 백엔드 서버입니다.
FastAPI를 기반으로 설계되었으며, 사용자의 법률 관련 주장을 분석하고 판례 및 조문을 검증하는 RAG(Retrieval-Augmented Generation) 파이프라인과 비전 AI 기능 등을 제공합니다.

## 🛠️ 기술 스택 (Tech Stack)

- **Web Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (SQLAlchemy ORM, Alembic)
- **Vector DB**: ChromaDB
- **AI & LLM**: OpenAI API (gpt-4o, gpt-4o-mini), LangChain
- **Package Manager**: uv

## 📁 주요 디렉토리 구조

- `app/core/`: 애플리케이션 핵심 설정 (`config.py` 등) 및 전역 구성.
- `app/api/`: REST API 라우터 정의 위치.
- `app/services/`: 비즈니스 로직, 외부 AI/API 연동 (`vision_service.py`, `hook_service.py`, `prompts.py` 등).
- `app/models/`: 데이터베이스 모델 (SQLAlchemy).
- `app/schemas/`: Pydantic 기반의 데이터 검증 및 입출력 스키마.
- `app/plugins/`: 판례 검색 등 외부 확장 플러그인 로직.

## 🚀 로컬 개발 셋업 (Setup Guide)

1. **환경 변수 설정**
   `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, `OPENAI_API_KEY` 및 DB 정보 등 필요한 값을 입력합니다.
   ```bash
   cp .env.example .env
   ```

2. **패키지 설치 및 동기화**
   백엔드는 `uv` 의존성 관리자를 사용합니다. 가상환경 및 패키지를 설치합니다:
   ```bash
   uv sync
   ```

3. **DB 실행 및 마이그레이션 (선택)**
   PostgreSQL이 필요하며, 최상위 디렉토리의 `docker-compose.yml`을 통해 DB 컨테이너를 실행하는 것을 권장합니다. 로컬 DB 셋업이 완료되면 Alembic으로 스키마 마이그레이션을 진행합니다.

4. **로컬 개발 서버 실행**
   ```bash
   uv run fastapi dev app/main.py
   ```
   서버가 정상적으로 실행되면 브라우저에서 `http://localhost:8000/docs` 경로로 접속하여 Swagger OpenAPI 기반의 API 문서를 확인할 수 있습니다.
