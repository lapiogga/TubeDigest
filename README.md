# TubeDigest

YouTube 구독 채널을 AI로 자동 분류하고 최근 3일 영상을 한눈에 보여주는 웹 앱.

## 주요 기능

- **Google OAuth 로그인** — YouTube 구독 권한 포함
- **AI 카테고리 분류** — Gemini가 채널을 계층형 카테고리로 자동 분류 (예: IT/Tech > AI)
- **최근 3일 영상** — 구독 동기화 시 최근 3일 영상 자동 수집
- **계층형 사이드바** — 부모/자식 카테고리, 채널 수 표시, 접기/펼치기
- **채널 바로가기** — 채널명 클릭 시 YouTube 새 탭 오픈

## 기술 스택

| 구분 | 기술 |
|------|------|
| 프런트엔드 | Next.js 16, TypeScript, Tailwind CSS, NextAuth |
| 백엔드 | FastAPI, Python 3.11+, SQLite / Turso |
| AI | Google Gemini (`gemini-3-flash-preview`) |
| 인증 | Google OAuth 2.0 (youtube.readonly) |

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Google Cloud 프로젝트 (OAuth 2.0 클라이언트 + YouTube Data API v3 활성화)
- Gemini API 키 (유료 티어 권장)

### 백엔드

```cmd
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`backend/.env` 파일 생성:

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GEMINI_API_KEY=your_gemini_key
JWT_SECRET_KEY=your_random_secret_32chars
NEXTAUTH_SYNC_SECRET=your_sync_secret
DATABASE_URL=sqlite:///./tubedigest.db
```

실행:

```cmd
uvicorn main:app --port 8003
```

### 프런트엔드

```cmd
cd frontend
npm install
```

`frontend/.env.local` 파일 생성:

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
NEXTAUTH_SECRET=your_nextauth_secret
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8003
NEXTAUTH_SYNC_SECRET=your_sync_secret
```

실행:

```cmd
npm run dev
```

### Google Cloud 설정

1. OAuth 2.0 클라이언트 생성 (웹 애플리케이션)
2. 승인된 리디렉션 URI: `http://localhost:3000/api/auth/callback/google`
3. YouTube Data API v3 활성화
4. OAuth 동의 화면 → 테스트 사용자 추가

## 사용 방법

1. `http://localhost:3000` 접속
2. **Google로 로그인** 클릭
3. **구독 동기화** 버튼 클릭 → Gemini AI가 채널 분류 + 최근 영상 수집
4. 좌측 카테고리 사이드바에서 원하는 카테고리 선택

## 프로젝트 구조

```
TubeDigest/
├── backend/          # FastAPI 백엔드
├── frontend/         # Next.js 프런트엔드
├── docs/
│   └── PROGRESS.md   # 개발 진행 이력
├── CHANGELOG.md      # 변경 이력
├── CLAUDE.md         # AI 개발 가이드
└── README.md
```

## 변경 이력

[CHANGELOG.md](./CHANGELOG.md) 참조

## 개발 진행 이력

[docs/PROGRESS.md](./docs/PROGRESS.md) 참조
