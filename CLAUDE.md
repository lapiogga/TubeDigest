# TubeDigest - CLAUDE.md

> 최종 갱신: 2026-03-06

## 프로젝트 개요

YouTube 구독 채널을 AI로 자동 분류하고 최근 3일 영상을 카드 형태로 보여주는 웹 앱.

**흐름**: Google OAuth 로그인 → YouTube 구독 동기화 → Gemini AI 카테고리 분류 → 최근 3일 영상 자동 수집 → 계층형 카테고리 탐색

**GitHub**: https://github.com/lapiogga/TubeDigest

---

## 아키텍처

```
TubeDigest/
├── backend/                    # FastAPI (Python 3.11+)
│   ├── main.py                 # 앱 진입점, CORS 설정
│   ├── database.py             # DB 연결 (SQLite 로컬 / Turso 원격)
│   ├── auth/
│   │   └── jwt.py              # JWT 검증 (get_current_user)
│   ├── routers/
│   │   ├── auth.py             # POST /api/auth/sync
│   │   └── youtube.py          # YouTube 관련 API 전체
│   └── services/
│       ├── youtube.py          # YouTube Data API v3 래퍼
│       └── gemini.py           # Gemini AI (분류/요약)
├── frontend/                   # Next.js 16 (TypeScript)
│   ├── next.config.ts          # remotePatterns (이미지 도메인)
│   └── src/
│       ├── app/
│       │   ├── page.tsx                    # 메인 페이지 (전체 UI)
│       │   ├── api/auth/[...nextauth]/     # NextAuth 핸들러
│       │   ├── api/youtube/               # Next.js → FastAPI 프록시 라우트
│       │   └── layout.tsx
│       ├── components/
│       │   └── Providers.tsx              # NextAuth SessionProvider
│       └── types/
│           └── next-auth.d.ts             # Session 타입 확장
├── docs/
│   └── PROGRESS.md             # 진행 이력 (타임스탬프 포함)
├── CHANGELOG.md                # 변경 이력
├── README.md                   # 프로젝트 소개 및 설치 가이드
└── .gitignore
```

---

## 백엔드

### 실행 (Windows)

```cmd
cd backend
.venv\Scripts\activate
uvicorn main:app --port 8003
```

> `--reload` 플래그 사용 금지. Windows에서 child process가 .env를 로드 못하는 문제 발생.

### 환경변수 (`backend/.env`)

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GEMINI_API_KEY=
JWT_SECRET_KEY=               # 필수 — 없으면 /api/auth/sync 500
NEXTAUTH_SYNC_SECRET=         # 선택 — NextAuth→백엔드 인증 헤더
TURSO_DATABASE_URL=           # 없으면 로컬 SQLite 사용
TURSO_AUTH_TOKEN=
DATABASE_URL=sqlite:///./tubedigest.db
```

### DB 스키마

```sql
users          -- id, google_id, email, name, access_token, refresh_token
subscriptions  -- id, user_id, channel_id, channel_title, channel_description,
               --    thumbnail_url, category
videos         -- id, subscription_id, video_id, title, description,
               --    published_at, thumbnail_url, ai_summary
```

- 기본값: `tubedigest.db` (SQLite). `TURSO_*` 환경변수 있으면 Turso(libsql) 사용.

### API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/auth/sync` | NextAuth 로그인 시 유저 DB 동기화 + JWT 발급 |
| GET | `/api/youtube/categories` | 카테고리 목록 + 채널 수 반환 |
| GET | `/api/youtube/subscriptions?category=` | 구독 채널 + 최근 3일 영상 반환 |
| POST | `/api/youtube/sync-subscriptions` | 구독 동기화 + Gemini 분류 + 3일 영상 저장 |
| POST | `/api/youtube/summarize-recent?channel_id=` | 특정 채널 최근 7일 영상 요약 (Gemini) |

### Gemini 서비스

- **모델**: `gemini-3-flash-preview` (유료 티어)
- **`categorize_channels()`**: `channel_id` 기반 매핑, 50개 배치 처리
  - 반환: `dict[channel_id → category]`
- **`summarize_videos()`**: 채널 최근 영상 → 3~4문장 트렌드 요약

### YouTube API 비용 최적화

| 메서드 | API | 단위 비용 |
|--------|-----|-----------|
| 구독 목록 | `subscriptions.list` | 1 unit / 50개 |
| 최근 영상 수집 | `playlistItems.list` | 1 unit / 채널 |
| 영상 요약용 | `search.list` | 100 unit / 채널 |

> 동기화 시 `playlistItems.list` 사용 (uploads 플레이리스트 = `UU` + `channel_id[2:]`)

---

## 프런트엔드

### 실행

```cmd
cd frontend
npm run dev   # http://localhost:3000
```

### 환경변수 (`frontend/.env.local`)

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8003
NEXTAUTH_SYNC_SECRET=
```

### 인증 흐름

1. `signIn("google")` → Google OAuth (youtube.readonly 스코프)
2. NextAuth `jwt` 콜백 → `/api/auth/sync` 호출 → `backendToken` 획득
3. `backendToken`은 JWT에만 저장 (클라이언트 session 미노출)
4. API 요청: Next.js 서버사이드 프록시 경유 → `getToken()`으로 backendToken 추가

### 주요 UI 구성

- **사이드바**: 계층형 카테고리 (부모 > 자식), 접기/펼치기, 채널 수 표시
- **메인**: 구독 채널별 최근 3일 영상 카드 (썸네일, 제목, 날짜, AI 요약)
- **채널명**: 클릭 시 YouTube 채널 새 탭 오픈

### next.config.ts 이미지 도메인

```typescript
remotePatterns: [
  { hostname: "lh3.googleusercontent.com" },  // Google 프로필
  { hostname: "yt3.ggpht.com" },              // YouTube 채널 썸네일
  { hostname: "i.ytimg.com" },                // YouTube 영상 썸네일
  { hostname: "ui-avatars.com" },             // 프로필 폴백
]
```

---

## 개발 주의사항

- **포트**: 백엔드 8003, 프런트엔드 3000. 충돌 시 `.next` 삭제 후 재기동
- **모델명**: `gemini-3-flash-preview` (API ID). `gemini-3.0-pro` 등 구 모델명 사용 금지
- **카테고리 매핑**: `channel_id` 키 사용. 채널명은 Gemini가 변형할 수 있어 신뢰 불가
- **3일 필터**: 영상 표시에만 적용. 카테고리 표시 기준은 구독 채널 유무
- **DB 초기화**: 카테고리 재분류 시 `UPDATE subscriptions SET category='Uncategorized'` 후 재동기화

---

## TODO

- [ ] 토큰 만료 처리 (refresh_token 갱신 로직)
- [ ] ai_summary 자동 생성 (현재 수동 `summarize-recent` 호출)
- [ ] 영상 클릭 시 YouTube 링크 연결
- [ ] 동기화 진행률 표시 (채널 수 많을 때 수십 초 소요)
- [ ] Turso 프로덕션 DB 전환

---

## 팀 에이전트 구조

| 역할 | 담당 에이전트 |
|------|-------------|
| 총괄 관리자 / 기획 | planner (opus) |
| 설계 / 아키텍처 | architect (opus) |
| DB 설계 | database-reviewer (opus) |
| 구현 / 버그수정 | build-error-resolver (sonnet) |
| 테스트 | tdd-guide (opus), e2e-runner (sonnet) |

**원칙**: 모든 대화 한글, hub-and-spoke 보고 체계

## 개발 파이프라인

```
PLAN → TDD → CODE_REVIEW → HANDOFF-VERIFY
```
