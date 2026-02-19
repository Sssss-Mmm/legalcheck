# Legal/Regulation Fact Checker (법률 팩트체커)

일반인이 근로기준법, 부동산법 등 생활 법률을 쉽게 이해하고 확인할 수 있도록 돕는 AI 기반 팩트체크 서비스입니다.

## 프로젝트 구조
- `backend/`: FastAPI 기반 API 서버 (uv 패키지 관리)
- `frontend/`: Next.js 기반 웹 애플리케이션

## 설치 및 실행 방법 (Setup Guide)

### 1. 필수 요구사항
- Python 3.10 이상
- uv (Python 패키지 관리자)
- Node.js 18 이상 (npm 포함)
- OpenAI API Key

### 2. 백엔드 설정 (Backend with uv)
이 프로젝트는 **uv**를 사용하여 패키지를 관리합니다.

```bash
# uv 설치 (이미 설치된 경우 생략)
# curl -LsSf https://astral.sh/uv/install.sh | sh
# 또는 pip install uv

cd backend

# 가상환경 생성 및 의존성 설치 (pyproject.toml 기반)
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r pyproject.toml  # 또는 uv sync (프로젝트 설정에 따라 다름)
# 현재 설정은 pyproject.toml을 사용하므로:
uv sync

# 환경변수 설정
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY를 입력하세요.
```

### 3. 프론트엔드 설정 (Frontend)
```bash
# Next.js 프로젝트 생성 (프로젝트 루트에서 실행)
npx -y create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm

# (생성 후) 프론트엔드 실행
cd frontend
npm run dev
```

### 4. 백엔드 실행
```bash
# backend 디렉토리에서 실행
uv run uvicorn main:app --reload
```
