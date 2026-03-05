# TubeDigest - CLAUDE.md

## 프로젝트 개요

YouTube 구독 채널을 AI로 자동 분류하고 최근 영상을 주간 요약해주는 웹 앱.
- Google OAuth로 로그인 → YouTube 구독 목록 Sync → Gemini AI가 카테고리 분류 → 채널별 영상 요약 생성

---

## 아키텍처

```
TubeDigest/
├── backend/          # FastAPI (Python)
│   ├── main.py       # 앱 진입점, CORS 설정
│   ├── database.py   # DB 연결 (SQLite 로컬 / Turso 원격)
│   ├── routers/
│   │   ├── auth.py   # POST /api/auth/sync
│   │   └── youtube.py # YouTube 관련 API
│   └── services/
│       ├── youtube.py # YouTube Data API v3 래퍼
│       └── gemini.py  # Gemini AI (분류/요약)
├── frontend/         # Next.js 16 (TypeScript)
│   └── src/
│       ├── app/
│       │   ├── page.tsx              # 메인 페이지
│       │   ├── api/auth/[...nextauth]/ # NextAuth 핸들러
│       │   └── layout.tsx
│       ├── components/
│       │   └── Providers.tsx         # NextAuth SessionProvider
│       └── types/
│           └── next-auth.d.ts        # Session 타입 확장
└── docker-compose.yml # PostgreSQL (포트 5435)
```

---

## 백엔드

### 실행

```bash
cd backend
.venv/Scripts/activate   # Windows
uvicorn main:app --reload --port 8000
```

### 환경변수 (.env)

```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GEMINI_API_KEY=
TURSO_DATABASE_URL=      # 없으면 로컬 SQLite 사용
TURSO_AUTH_TOKEN=        # 없으면 로컬 SQLite 사용
DATABASE_URL=sqlite:///./tubedigest.db
```

### DB 스키마

```sql
users           -- id, google_id, email, name, access_token, refresh_token
subscriptions   -- id, user_id, channel_id, channel_title, thumbnail_url, category
videos          -- id, subscription_id, video_id, title, description, published_at, thumbnail_url, ai_summary
```

- DB: 기본값은 `tubedigest.db` (SQLite). `TURSO_*` 환경변수 있으면 Turso(libsql) 사용.
- `docker-compose.yml`의 PostgreSQL은 현재 미사용 (레거시).

### API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/auth/sync` | NextAuth 로그인 시 유저 DB 동기화 |
| GET | `/api/youtube/sync-subscriptions?user_id=` | YouTube 구독 목록 가져와 DB 저장 + Gemini 카테고리 분류 |
| GET | `/api/youtube/summarize-recent?channel_id=&user_id=` | 특정 채널 최근 7일 영상 요약 (Gemini) |

### Gemini 사용

- 모델: `gemini-3.0-pro`
- `categorize_channels()`: 채널 목록 → JSON `[{channel_title, category}]` 반환
- `summarize_videos()`: 영상 목록 → 채널 트렌드 요약 텍스트 반환
- Gemini 응답에 markdown 코드블록 포함될 수 있어 파싱 시 strip 처리 필요

---

## 프런트엔드

### 실행

```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

### 환경변수 (.env.local)

```
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
NEXTAUTH_SECRET=
NEXTAUTH_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 인증 흐름

1. `signIn("google")` → Google OAuth (youtube.readonly 스코프 포함)
2. NextAuth `jwt` 콜백 → 백엔드 `/api/auth/sync` 호출 → DB user_id 획득
3. `session.user.id`에 DB user_id 저장
4. 이후 모든 API 요청에 `user_id` 쿼리 파라미터로 전달

### 현재 상태 (미완성)

- 카테고리 사이드바: 하드코딩된 더미 데이터 (실제 API 연동 필요)
- 비디오 요약 섹션: 더미 데이터 (실제 API 연동 필요)
- Sync 버튼: 구현 완료

---

## 미구현 / TODO

- [ ] `GET /api/youtube/categories?user_id=` 엔드포인트 추가
- [ ] `GET /api/youtube/subscriptions?user_id=&category=` 엔드포인트 추가
- [ ] 프런트엔드 카테고리 사이드바 실제 데이터 연동
- [ ] 프런트엔드 채널별 요약 카드 실제 데이터 연동
- [ ] `ai_summary` 필드 활용 (현재 미사용)
- [ ] 토큰 만료 처리 (refresh_token 갱신 로직)

---

## 팀 에이전트 구조

### 역할 정의

| 역할 | 책임 | 사용 에이전트 |
|------|------|--------------|
| **총괄 관리자** | 전체 진행 조율, 우선순위 결정, 팀 간 의존성 관리 | planner (opus) |
| **기획 담당자** | 요구사항 분석, 기능 명세 작성, 사용자 스토리 정의 | planner (opus) |
| **설계 담당자** | 시스템 아키텍처, API 설계, DB 스키마 설계 | architect (opus) |
| **데이터 담당자** | DB 스키마 최적화, 쿼리 설계, 마이그레이션 | database-reviewer (opus) |
| **개발 담당자** | 기능 구현, 코드 작성, 버그 수정 | build-error-resolver (sonnet) |
| **테스트 담당자** | 테스트 작성, E2E 검증, 품질 보증 | tdd-guide (opus), e2e-runner (sonnet) |

### 의사소통 원칙

- **모든 대화는 한글** 사용 (코드 식별자/주석 제외)
- 팀 에이전트 간 보고는 총괄 관리자 경유 (hub-and-spoke)
- 기술 조율이 필요한 경우에만 peer-to-peer 예외 허용
- 각 역할은 필요 시 Sub Agent를 생성하여 업무 위임 가능

---

## 개발 파이프라인

Claude Forge 표준 파이프라인을 적용한다.

```
PLAN → TDD → CODE_REVIEW → HANDOFF-VERIFY
```

### 단계별 상세

#### 1. PLAN (구현계획 수립)
- **담당**: 총괄 관리자 + 기획 담당자 + 설계 담당자
- **도구**: `planner` 에이전트, `architect` 에이전트
- **산출물**: 구현 계획서, API 명세, DB 스키마 변경안
- **명령**: `/plan`

#### 2. TDD (테스트 주도 개발)
- **담당**: 테스트 담당자 → 개발 담당자
- **도구**: `tdd-guide` 에이전트
- **순서**: RED(실패 테스트 작성) → GREEN(최소 구현) → IMPROVE(리팩토링)
- **기준**: 커버리지 80% 이상
- **명령**: `/tdd`

#### 3. CODE_REVIEW (코드 리뷰)
- **담당**: 설계 담당자 + 데이터 담당자
- **도구**: `code-reviewer` 에이전트, `security-reviewer` 에이전트
- **기준**: CRITICAL/HIGH 이슈 반드시 해결, MEDIUM 가능한 해결
- **명령**: `/code-review`

#### 4. HANDOFF-VERIFY (최종 검증)
- **담당**: 테스트 담당자
- **도구**: `verify-agent` 에이전트 (독립 컨텍스트)
- **내용**: 전체 기능 동작 검증, E2E 테스트
- **명령**: `/handoff-verify`

---

## 개발 주의사항

- `turso` 패키지는 SQLite와 Turso(libsql) 모두 지원. URL 포맷에 주의:
  - 로컬: 파일 경로 문자열
  - Turso: `libsql://` → `https://` 로 변환 후 연결
- Gemini 응답은 항상 JSON 파싱 전 마크다운 블록 strip 처리
- NextAuth session에 커스텀 필드(`id`, `accessToken`, `refreshToken`) 사용 → `src/types/next-auth.d.ts` 참조
