# CHANGELOG

모든 주요 변경사항을 기록합니다. 날짜 기준 역순 정렬.

---

## [0.3.0] - 2026-03-06

### 추가
- 카테고리 사이드바 계층형 표시 (부모 > 자식 구조, 접기/펼치기)
- 카테고리명 옆 구독 채널 수 표시 (부모는 자식 합산)
- 구독 채널 0개 카테고리 자동 숨김
- 채널명 클릭 → YouTube 채널 새 탭 오픈
- 부모 카테고리 클릭 시 하위 전체 구독 필터 (LIKE prefix 매칭)
- 사이드바 최대 800px 스크롤 처리
- 최근 3일 이내 영상만 메인 콘텐츠에 표시
- 구독 동기화 시 `playlistItems.list` (1 unit/채널)로 최근 영상 자동 저장
- 동기화 완료 메시지에 저장된 영상 수 포함

### 변경
- 카테고리 API 응답에 `category_counts` 필드 추가
- 구독 API에 3일 날짜 필터 추가 (published_at >= 3일 전)
- 구독 API 카테고리 필터: 정확 매칭 + prefix LIKE 매칭 병행

---

## [0.2.0] - 2026-03-06

### 추가
- `GET /api/youtube/categories` 엔드포인트 구현
- `GET /api/youtube/subscriptions?category=` 엔드포인트 구현
- 프런트엔드 카테고리 사이드바 실제 API 연동
- 프런트엔드 채널별 영상 카드 실제 API 연동
- next/image `<Image>` 컴포넌트 적용 (프로필, 채널 썸네일, 영상 썸네일)
- `next.config.ts` 외부 이미지 도메인 remotePatterns 설정

### 수정
- Gemini 카테고리 분류 버그: `channel_title` 매핑 → `channel_id` 매핑으로 변경
  - 채널명 불일치로 전체 Uncategorized 분류되던 문제 해결
- Gemini 분류 대량 구독 처리: 50개 배치 처리 추가
- Gemini 모델: `gemini-3.0-pro` (미존재) → `gemini-3-flash-preview`
- 구독 동기화 API: GET → POST 변경 (DB 쓰기 작업 의미론 준수)
- JWT 인증: Bearer 헤더 제거, Next.js 서버사이드 프록시 경유 방식 적용

### 인프라
- `backend/.env`에 `JWT_SECRET_KEY` 필수 추가 (없으면 /api/auth/sync 500)
- uvicorn `--reload` 플래그 제거 (Windows child process .env 미로드 문제)
- 백엔드 포트 8000 → 8003 (포트 충돌 회피)
- `.gitignore` 추가 (.env, __pycache__, *.db, .next 등)

---

## [0.1.0] - 2026-03-05

### 초기 구현
- FastAPI 백엔드 기본 구조 (main.py, database.py, routers, services)
- Next.js 16 프런트엔드 기본 구조
- Google OAuth 로그인 (NextAuth, youtube.readonly 스코프)
- `POST /api/auth/sync`: 로그인 시 유저 DB 동기화 + JWT 발급
- `POST /api/youtube/sync-subscriptions`: YouTube 구독 목록 동기화
- Gemini AI 채널 카테고리 분류 (`categorize_channels`)
- Gemini AI 영상 요약 (`summarize_videos`)
- SQLite 로컬 DB / Turso 원격 DB 이중 지원
- 기본 UI: 로그인 화면, 메인 대시보드, 동기화 버튼
