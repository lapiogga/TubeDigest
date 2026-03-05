# TubeDigest 개발 진행 이력

---

## 2026-03-06 (세션 3)

### 완료 작업

#### 기능 추가
| 작업 | 파일 | 커밋 |
|------|------|------|
| 구독취소 버튼 UI (채널 헤더 우측) | `frontend/src/app/page.tsx` | `3912a7b` |
| 구독 신청일 표시 (구독일: MM월 DD일) | `frontend/src/app/page.tsx` | `3912a7b` |
| DELETE /api/youtube/subscriptions/{channel_id} | `backend/routers/youtube.py` | `3912a7b` |
| YouTube API 구독 취소 (unsubscribe_channel) | `backend/services/youtube.py` | `3912a7b` |
| Next.js 프록시: [channel_id]/route.ts | `frontend/src/app/api/youtube/subscriptions/` | `3912a7b` |
| DB subscribed_at 컬럼 + 마이그레이션 | `backend/database.py` | `3912a7b` |
| OAuth 스코프: youtube.readonly → youtube | `frontend/src/app/api/auth/[...nextauth]/route.ts` | `3912a7b` |

---

## 2026-03-06 (세션 2)

### 완료 작업

#### UI 개선
| 시간 | 작업 | 커밋 |
|------|------|------|
| 오전 | `<img>` → `next/image <Image>` 교체 (프로필/채널/영상 썸네일) | `23f9295` |
| 오전 | next.config.ts remotePatterns 4개 도메인 추가 | `23f9295` |
| 오후 | 계층형 카테고리 사이드바 (부모>자식, 접기/펼치기) | `ccc5fc8` |
| 오후 | 최근 3일 이내 영상만 표시 | `ccc5fc8` |
| 오후 | 구독 동기화 시 playlistItems.list로 영상 자동 저장 | `ccc5fc8` |
| 오후 | 채널명 클릭 → YouTube 새 탭 | `d19fce5` |
| 오후 | 카테고리 invisible (구독 없는 카테고리 숨김) | `d19fce5` |
| 오후 | 카테고리 간격 조밀화 | `d19fce5` |
| 오후 | 카테고리명 옆 구독 채널 수 표시 | `b97722d` |
| 오후 | 구독 0개 카테고리 완전 숨김 필터 | `862005b` |

#### 버그 수정
| 증상 | 원인 | 해결 |
|------|------|------|
| 전체 Uncategorized | channel_title 매핑 불일치 | channel_id 키로 변경 |
| Gemini 429 오류 | gemini-2.0-flash 무료 티어 소진 | gemini-3-flash-preview 전환 |
| 카테고리 전혀 안보임 | 카테고리 API에 3일 필터 과적용 | 카테고리 기준을 구독 유무로 복구 |

---

## 2026-03-05 (세션 1)

### 완료 작업

#### 인프라 / 인증
| 작업 | 결과 |
|------|------|
| Google OAuth 401 (invalid_client) | GOOGLE_CLIENT_SECRET 올바른 값으로 교체 |
| 403 access_denied | OAuth 동의 화면 테스트 사용자 등록 |
| OAuthCallback 오류 | Next.js 포트 3000 고정 |
| 서버 연동 실패 | JWT_SECRET_KEY 환경변수 추가 |
| uvicorn --reload .env 미로드 | --reload 제거, 포트 8003 사용 |
| Turbopack 캐시 손상 | .next 삭제 후 재기동 |

#### 기능 구현
| 작업 | 파일 |
|------|------|
| GET /api/youtube/categories 구현 | `backend/routers/youtube.py` |
| GET /api/youtube/subscriptions 구현 | `backend/routers/youtube.py` |
| 프런트엔드 카테고리 실제 API 연동 | `frontend/src/app/page.tsx` |
| 프런트엔드 영상 카드 실제 API 연동 | `frontend/src/app/page.tsx` |
| N+1 쿼리 → JOIN 단일 쿼리 최적화 | `backend/routers/youtube.py` |
| Gemini 분류: channel_id 기반 매핑 | `backend/services/gemini.py` |
| Gemini 50개 배치 처리 | `backend/services/gemini.py` |
| .gitignore 추가 | `.gitignore` |
| GitHub 저장소 초기 배포 | `21fa07d` |

---

## 현재 상태 (2026-03-06 세션 3 기준)

### 작동 중
- Google OAuth 로그인 (youtube 스코프)
- 구독 동기화 + AI 카테고리 분류
- 최근 3일 영상 자동 수집
- 계층형 카테고리 사이드바 (구독 수 표시)
- 채널명 클릭 → YouTube 채널 새 탭
- 채널 구독취소 (YouTube API + DB 동시 삭제)
- 구독 신청일 표시

### 미완성
- [ ] ai_summary 자동 생성 (현재 summarize-recent 수동 호출)
- [ ] 영상 제목 클릭 → YouTube 링크
- [ ] 동기화 진행률 UI (채널 많을 때 대기 시간 없음)
- [ ] refresh_token 갱신 로직
- [ ] Turso 프로덕션 전환

---

## 진행 예정 (다음 세션)

1. ai_summary 자동 생성 파이프라인 (동기화 시 배치 요약)
2. 영상 제목 클릭 → YouTube 영상 링크
3. 동기화 진행률 표시 (SSE 또는 폴링)
