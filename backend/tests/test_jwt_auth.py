"""
TDD — JWT 인증 모듈 테스트 (인증은 보안 핵심 → 커버리지 100% 목표)

테스트 범위:
  Phase 1-A: create_access_token / decode_access_token 단위 테스트
  Phase 1-B: get_current_user FastAPI 의존성 통합 테스트
  Phase 2:   /api/auth/sync 응답에 token 포함 확인
  Phase 3:   보호된 엔드포인트 인증 요구 확인
"""
import os
import sqlite3
import time
import pytest
import jwt as pyjwt
from fastapi.testclient import TestClient

# JWT_SECRET_KEY 테스트 환경 설정 (실제 환경변수보다 먼저)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")

from main import app
import database

SECRET = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"


# ── 공통 헬퍼 ──────────────────────────────────────────────────────────────

def make_test_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE, email TEXT UNIQUE,
            name TEXT, access_token TEXT, refresh_token TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, channel_id TEXT, channel_title TEXT,
            channel_description TEXT, thumbnail_url TEXT,
            category TEXT DEFAULT 'Uncategorized'
        );
        CREATE TABLE videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER, video_id TEXT, title TEXT,
            description TEXT, published_at DATETIME,
            thumbnail_url TEXT, ai_summary TEXT
        );
    """)
    con.commit()
    return con


def make_client(con: sqlite3.Connection) -> TestClient:
    def override():
        try:
            yield con
        finally:
            pass
    app.dependency_overrides[database.get_db] = override
    return TestClient(app)


def make_valid_token(user_id: int = 1, secret: str = SECRET) -> str:
    """테스트용 유효 JWT 생성"""
    from datetime import datetime, timedelta, timezone
    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
    }
    return pyjwt.encode(payload, secret, algorithm=ALGORITHM)


# ── Phase 1-A: create_access_token / decode_access_token ──────────────────

class TestCreateAccessToken:

    def test_토큰_생성_성공(self):
        """유효한 user_id로 JWT 토큰을 생성해야 한다"""
        from auth.jwt import create_access_token
        token = create_access_token(user_id=42)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_생성된_토큰_디코딩_가능(self):
        """생성된 토큰은 올바른 user_id를 포함해야 한다"""
        from auth.jwt import create_access_token
        token = create_access_token(user_id=42)
        payload = pyjwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert payload["sub"] == "42"

    def test_토큰에_만료시간_포함(self):
        """생성된 토큰에 exp 클레임이 있어야 한다"""
        from auth.jwt import create_access_token
        token = create_access_token(user_id=1)
        payload = pyjwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_만료시간은_7일_이후(self):
        """만료 시간은 현재로부터 7일 후여야 한다"""
        from auth.jwt import create_access_token
        from datetime import datetime, timezone
        before = datetime.now(timezone.utc).timestamp()
        token = create_access_token(user_id=1)
        payload = pyjwt.decode(token, SECRET, algorithms=[ALGORITHM])
        after = datetime.now(timezone.utc).timestamp()
        # 6일 이상 ~ 7일 1분 이하
        assert payload["exp"] > before + 6 * 24 * 3600
        assert payload["exp"] < after + 7 * 24 * 3600 + 60


class TestDecodeAccessToken:

    def test_유효한_토큰_디코딩(self):
        """유효한 토큰에서 user_id(int)를 반환해야 한다"""
        from auth.jwt import decode_access_token
        token = make_valid_token(user_id=99)
        result = decode_access_token(token)
        assert result == 99

    def test_잘못된_서명_토큰은_예외(self):
        """서명이 다른 토큰은 HTTPException 401을 발생시켜야 한다"""
        from auth.jwt import decode_access_token
        from fastapi import HTTPException
        bad_token = make_valid_token(user_id=1, secret="wrong-secret")
        with pytest.raises(HTTPException) as exc:
            decode_access_token(bad_token)
        assert exc.value.status_code == 401

    def test_만료된_토큰은_예외(self):
        """만료된 토큰은 HTTPException 401을 발생시켜야 한다"""
        from auth.jwt import decode_access_token
        from fastapi import HTTPException
        from datetime import datetime, timedelta, timezone
        payload = {"sub": "1", "exp": datetime.now(timezone.utc) - timedelta(seconds=1)}
        expired_token = pyjwt.encode(payload, SECRET, algorithm=ALGORITHM)
        with pytest.raises(HTTPException) as exc:
            decode_access_token(expired_token)
        assert exc.value.status_code == 401

    def test_형식_잘못된_토큰은_예외(self):
        """토큰 형식이 잘못된 경우 HTTPException 401을 발생시켜야 한다"""
        from auth.jwt import decode_access_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_access_token("not.a.valid.jwt.token")
        assert exc.value.status_code == 401

    def test_빈_토큰은_예외(self):
        """빈 문자열 토큰은 HTTPException 401을 발생시켜야 한다"""
        from auth.jwt import decode_access_token
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            decode_access_token("")
        assert exc.value.status_code == 401


# ── Phase 1-B: get_current_user FastAPI 의존성 통합 테스트 ─────────────────

class TestProtectedEndpoints:

    def setup_method(self):
        self.con = make_test_db()
        # 테스트 유저 삽입
        self.con.execute(
            "INSERT INTO users (google_id, email, name, access_token) VALUES (?, ?, ?, ?)",
            ("g-001", "test@example.com", "테스트유저", "tok")
        )
        self.con.commit()
        self.user_id = self.con.execute("SELECT id FROM users WHERE google_id='g-001'").fetchone()[0]
        self.client = make_client(self.con)

    def teardown_method(self):
        app.dependency_overrides.clear()
        self.con.close()

    def _auth_header(self, user_id: int | None = None) -> dict:
        uid = user_id if user_id is not None else self.user_id
        token = make_valid_token(uid)
        return {"Authorization": f"Bearer {token}"}

    def test_인증없이_categories_접근_401(self):
        """Authorization 헤더 없이 /categories 접근은 401이어야 한다"""
        res = self.client.get("/api/youtube/categories")
        assert res.status_code == 401 or res.status_code == 403

    def test_인증없이_subscriptions_접근_401(self):
        """Authorization 헤더 없이 /subscriptions 접근은 401이어야 한다"""
        res = self.client.get("/api/youtube/subscriptions")
        assert res.status_code == 401 or res.status_code == 403

    def test_유효한_토큰으로_categories_접근_200(self):
        """유효한 Bearer 토큰으로 /categories 접근은 200이어야 한다"""
        res = self.client.get("/api/youtube/categories", headers=self._auth_header())
        assert res.status_code == 200
        assert "categories" in res.json()

    def test_유효한_토큰으로_subscriptions_접근_200(self):
        """유효한 Bearer 토큰으로 /subscriptions 접근은 200이어야 한다"""
        res = self.client.get("/api/youtube/subscriptions", headers=self._auth_header())
        assert res.status_code == 200
        assert "subscriptions" in res.json()

    def test_잘못된_토큰으로_접근_401(self):
        """잘못된 토큰으로 /categories 접근은 401이어야 한다"""
        res = self.client.get(
            "/api/youtube/categories",
            headers={"Authorization": "Bearer invalid.token.here"}
        )
        assert res.status_code == 401

    def test_존재하지_않는_유저_토큰_404(self):
        """DB에 없는 user_id로 된 토큰은 404이어야 한다"""
        res = self.client.get(
            "/api/youtube/categories",
            headers=self._auth_header(user_id=99999)
        )
        assert res.status_code == 404


# ── Phase 2: /api/auth/sync 응답에 token 포함 ─────────────────────────────

class TestAuthSyncReturnsToken:

    def setup_method(self):
        self.con = make_test_db()
        self.client = make_client(self.con)

    def teardown_method(self):
        app.dependency_overrides.clear()
        self.con.close()

    def test_sync_응답에_token_포함(self):
        """/api/auth/sync 응답에 JWT token 필드가 포함되어야 한다"""
        res = self.client.post("/api/auth/sync", json={
            "google_id": "g-new",
            "email": "new@example.com",
            "name": "신규유저",
            "access_token": "google-token",
        })
        assert res.status_code == 200
        data = res.json()
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

    def test_sync_token은_유효한_jwt(self):
        """/api/auth/sync 응답의 token은 디코딩 가능한 JWT여야 한다"""
        res = self.client.post("/api/auth/sync", json={
            "google_id": "g-jwt-test",
            "email": "jwt@example.com",
            "name": "JWT테스트",
            "access_token": "google-token",
        })
        token = res.json()["token"]
        payload = pyjwt.decode(token, SECRET, algorithms=[ALGORITHM])
        assert "sub" in payload
        assert int(payload["sub"]) > 0

    def test_sync_기존유저_재로그인_새_token_발급(self):
        """기존 유저가 재로그인해도 유효한 token을 반환해야 한다"""
        body = {
            "google_id": "g-existing",
            "email": "existing@example.com",
            "name": "기존유저",
            "access_token": "google-token",
        }
        self.client.post("/api/auth/sync", json=body)  # 최초 등록
        res = self.client.post("/api/auth/sync", json=body)  # 재로그인
        assert res.status_code == 200
        assert "token" in res.json()
