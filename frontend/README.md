# Legal Fact Checker Frontend

이 프로젝트는 **법률 팩트체커(Legal Fact Checker)** 서비스의 사용자 인터페이스(UI)를 구성하는 프론트엔드 웹 애플리케이션입니다.
Next.js (App Router)와 Tailwind CSS를 활용하여 구축되었습니다.

## 🛠️ 기술 스택 (Tech Stack)

- **Framework**: Next.js (App Router)
- **Library**: React
- **Styling**: Tailwind CSS v4
- **Authentication**: NextAuth.js (Google OAuth)
- **Language**: TypeScript

## ✨ 주요 기능 (Features)

- **팩트체크 대시보드**: 사용자 주장을 입력받아 백엔드 서버의 RAG/AI 엔진에 검증을 요청하는 메인 UI.
- **문서(이미지) 첨부 지원**: 근로계약서, 임금명세서 등의 이미지 업로드를 통한 비전 AI 기반 상황 검증 기능.
- **검증 결과 및 법률 문서 초안 뷰어**: TRUE / PARTIAL / FALSE 등 상태별 일관된 디자인(색상 뱃지 등) 및 상세한 법률 피드백 제공.
- **대화 히스토리 및 북마크**: 사용자의 지난 검증 기록 열람 기능 및 주요 세션 개별 저장.

## 🚀 로컬 개발 셋업 (Setup Guide)

1. **환경 변수 설정**
   루트 경로에 `.env.local` 파일을 생성하고 다음 필수 변수들을 입력합니다.
   ```env
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=본인만의_강력한_시크릿_문자열
   GOOGLE_CLIENT_ID=구글_클라이언트_ID
   GOOGLE_CLIENT_SECRET=구글_클라이언트_시크릿
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. **패키지 설치**
   아래 명령어 중 선호하는 패키지 매니저를 사용하여 의존성을 설치합니다.
   ```bash
   npm install
   # 또는
   yarn install
   # 또는
   pnpm install
   ```

3. **개발 서버 실행**
   ```bash
   npm run dev
   ```
   브라우저에서 [http://localhost:3000](http://localhost:3000) 페이지로 접속하여 정상 동작 여부를 확인합니다.
