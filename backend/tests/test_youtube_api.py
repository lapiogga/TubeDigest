"""
TDD - YouTube API 엔드포인트 테스트

Phase 1: ai_summary DB 저장
Phase 2: categories / subscriptions 조회 API
"""
import os
import sqlite3
import pytest
import jwt as pyjwt
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from main import app
import database

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
_JWT_SECRET = os.environ["JWT_SECRET_KEY"]


def _make_token(user_id: int) -> str:
    payload = {"sub": str(user_id), "exp": datetime.now(timezone.utc) + timedelta(days=7)}
    return pyjwt.encode(payload, _JWT_SECRET, algorithm="HS256")


def _auth(user_id: int) -> dict:
    return {"Authorization": f"Bearer {_make_token(user_id)}"}


# ── 공통 헬퍼 ──────────────────────────────────────────────────────────────

def make_test_db() -> sqlite3.Connection:
    """인메모리 SQLite DB 생성 및 스키마 초기화"""
    con = sqlite3.connect(":memory:", check_same_thread=False)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id TEXT UNIQUE, email TEXT UNIQUE,
            name TEXT, access_token TEXT, refresh_token TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER, channel_id TEXT, channel_title TEXT,
            channel_description TEXT, thumbnail_url TEXT,
            category TEXT DEFAULT 'Uncategorized',
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER, video_id TEXT, title TEXT,
            description TEXT, published_at DATETIME,
            thumbnail_url TEXT, ai_summary TEXT,
            FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
        );
    """)
    con.commit()
    return con


def seed_data(con: sqlite3.Connection):
    """테스트 시드 데이터 삽입, (user_id, sub_ids) 반환"""
    cur = con.cursor()
    cur.execute(
        "INSERT INTO users (google_id, email, name, access_token) VALUES (?, ?, ?, ?)",
        ("g-001", "test@example.com", "테스트유저", "token-abc")
    )
    user_id = cur.lastrowid

    cur.execute(
        "INSERT INTO subscriptions (user_id, channel_id, channel_title, thumbnail_url, category) VALUES (?, ?, ?, ?, ?)",
        (user_id, "ch-001", "AI 채널", "https://t1.jpg", "IT/Tech")
    )
    sub1 = cur.lastrowid

    cur.execute(
        "INSERT INTO subscriptions (user_id, channel_id, channel_title, thumbnail_url, category) VALUES (?, ?, ?, ?, ?)",
        (user_id, "ch-002", "요리 채널", "https://t2.jpg", "라이프스타일")
    )
    sub2 = cur.lastrowid

    cur.execute(
        "INSERT INTO subscriptions (user_id, channel_id, channel_title, thumbnail_url, category) VALUES (?, ?, ?, ?, ?)",
        (user_id, "ch-003", "코딩 강의", "https://t3.jpg", "IT/Tech")
    )
    sub3 = cur.lastrowid

    cur.execute(
        "INSERT INTO videos (subscription_id, video_id, title, published_at, ai_summary) VALUES (?, ?, ?, ?, ?)",
        (sub1, "v-001", "GPT-5 리뷰", "2026-03-01", "GPT-5는 놀랍습니다.")
    )
    cur.execute(
        "INSERT INTO videos (subscription_id, video_id, title, published_at, ai_summary) VALUES (?, ?, ?, ?, ?)",
        (sub2, "v-002", "파스타 레시피", "2026-03-02", None)
    )
    con.commit()
    return user_id, sub1, sub2, sub3


def make_client(con: sqlite3.Connection) -> TestClient:
    """DB 의존성을 인메모리 DB로 교체한 TestClient 반환"""
    def override():
        try:
            yield con
        finally:
            pass
    app.dependency_overrides[database.get_db] = override
    return TestClient(app)


# ── Phase 2: GET /api/youtube/categories ───────────────────────────────────

class TestCategoriesEndpoint:

    def setup_method(self):
        self.con = make_test_db()
        self.user_id, *_ = seed_data(self.con)
        self.client = make_client(self.con)

    def teardown_method(self):
        app.dependency_overrides.clear()
        self.con.close()

    def test_카테고리_목록_반환(self):
        """존재하는 카테고리 목록을 중복 없이 반환해야 한다"""
        res = self.client.get("/api/youtube/categories", headers=_auth(self.user_id))

        assert res.status_code == 200
        data = res.json()
        assert "categories" in data
        categories = data["categories"]
        assert "IT/Tech" in categories
        assert "라이프스타일" in categories
        assert categories.count("IT/Tech") == 1

    def test_구독_없는_유저는_빈_목록(self):
        """구독이 없는 유저는 빈 카테고리 목록을 반환해야 한다"""
        cur = self.con.cursor()
        cur.execute(
            "INSERT INTO users (google_id, email, name) VALUES (?, ?, ?)",
            ("g-999", "empty@example.com", "빈유저")
        )
        self.con.commit()
        empty_id = cur.lastrowid

        res = self.client.get("/api/youtube/categories", headers=_auth(empty_id))

        assert res.status_code == 200
        assert res.json()["categories"] == []

    def test_존재하지_않는_유저는_404(self):
        """존재하지 않는 user_id는 404를 반환해야 한다"""
        res = self.client.get("/api/youtube/categories", headers=_auth(99999))

        assert res.status_code == 404


# ── Phase 2: GET /api/youtube/subscriptions ────────────────────────────────

class TestSubscriptionsEndpoint:

    def setup_method(self):
        self.con = make_test_db()
        self.user_id, *_ = seed_data(self.con)
        self.client = make_client(self.con)

    def teardown_method(self):
        app.dependency_overrides.clear()
        self.con.close()

    def test_전체_구독_반환(self):
        """Bearer 토큰으로 모든 구독을 반환해야 한다"""
        res = self.client.get("/api/youtube/subscriptions", headers=_auth(self.user_id))

        assert res.status_code == 200
        data = res.json()
        assert "subscriptions" in data
        assert len(data["subscriptions"]) == 3

    def test_카테고리_필터_동작(self):
        """특정 category는 해당 카테고리 구독만 반환해야 한다"""
        res = self.client.get(
            "/api/youtube/subscriptions?category=IT/Tech",
            headers=_auth(self.user_id)
        )

        assert res.status_code == 200
        subs = res.json()["subscriptions"]
        assert len(subs) == 2
        for sub in subs:
            assert sub["category"] == "IT/Tech"

    def test_응답_필수_필드_포함(self):
        """구독 응답에 필수 필드가 모두 포함되어야 한다"""
        res = self.client.get("/api/youtube/subscriptions", headers=_auth(self.user_id))

        subs = res.json()["subscriptions"]
        required = {"id", "channel_id", "channel_title", "thumbnail_url", "category"}
        for sub in subs:
            assert required.issubset(sub.keys()), f"누락 필드: {required - sub.keys()}"

    def test_존재하지_않는_유저는_404(self):
        """존재하지 않는 user_id 토큰은 404를 반환해야 한다"""
        res = self.client.get("/api/youtube/subscriptions", headers=_auth(99999))

        assert res.status_code == 404

    def test_category_미지정시_전체_반환(self):
        """category 파라미터 없으면 전체 구독을 반환해야 한다"""
        res = self.client.get("/api/youtube/subscriptions", headers=_auth(self.user_id))

        assert res.status_code == 200
        assert len(res.json()["subscriptions"]) == 3


# ── Phase 1: ai_summary DB 저장 검증 ──────────────────────────────────────

class TestAiSummaryStorage:

    def setup_method(self):
        self.con = make_test_db()
        self.user_id, self.sub1, *_ = seed_data(self.con)
        self.client = make_client(self.con)

    def teardown_method(self):
        app.dependency_overrides.clear()
        self.con.close()

    def test_videos_테이블에_ai_summary_컬럼_존재(self):
        """videos 테이블에 ai_summary 컬럼이 존재해야 한다"""
        cur = self.con.cursor()
        cur.execute("PRAGMA table_info(videos)")
        columns = [row[1] for row in cur.fetchall()]
        assert "ai_summary" in columns

    def test_구독_응답에_videos_ai_summary_포함(self):
        """subscriptions 응답의 videos에 ai_summary 필드가 포함되어야 한다"""
        res = self.client.get(
            "/api/youtube/subscriptions?category=IT/Tech",
            headers=_auth(self.user_id)
        )

        assert res.status_code == 200
        subs = res.json()["subscriptions"]
        ai_channel = next((s for s in subs if s["channel_id"] == "ch-001"), None)
        assert ai_channel is not None
        assert ai_channel["videos"], "IT/Tech 채널에 영상이 있어야 한다"
        video = ai_channel["videos"][0]
        assert "ai_summary" in video
        assert video["ai_summary"] == "GPT-5는 놀랍습니다."
