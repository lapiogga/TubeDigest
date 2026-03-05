import os
import sqlite3
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN")


class _TursoCursor:
    """libsql_client.ClientSync.execute를 sqlite3 Cursor처럼 사용하는 어댑터."""

    def __init__(self, client):
        self._client = client
        self._rows = []
        self.lastrowid = None

    def execute(self, sql, params=()):
        from libsql_client import Statement
        result = self._client.execute(Statement(sql, list(params)))
        self._rows = result.rows
        self.lastrowid = result.last_insert_rowid
        return self

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class _TursoAdapter:
    """libsql_client.ClientSync를 sqlite3 Connection처럼 사용하는 어댑터."""

    def __init__(self, client):
        self._client = client

    def cursor(self):
        return _TursoCursor(self._client)

    def commit(self):
        pass  # Turso는 각 실행마다 자동 커밋

    def close(self):
        self._client.close()


def get_db():
    if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
        db_url = os.getenv("DATABASE_URL", "sqlite:///./tubedigest.db").replace("sqlite:///", "").replace("./", "")
        con = sqlite3.connect(db_url, check_same_thread=False)
        con.row_factory = sqlite3.Row
    else:
        import libsql_client
        https_url = TURSO_DATABASE_URL.replace("libsql://", "https://")
        client = libsql_client.create_client_sync(https_url, auth_token=TURSO_AUTH_TOKEN)
        con = _TursoAdapter(client)

    try:
        yield con
    finally:
        con.close()

def init_db():
    logger.info("Initializing Database with Raw SQL...")
    gen = get_db()
    con = next(gen)

    try:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                google_id TEXT UNIQUE,
                email TEXT UNIQUE,
                name TEXT,
                access_token TEXT,
                refresh_token TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id TEXT,
                channel_title TEXT,
                channel_description TEXT,
                thumbnail_url TEXT,
                category TEXT DEFAULT 'Uncategorized',
                subscribed_at DATETIME,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        # 기존 DB 마이그레이션: subscribed_at 컬럼 추가
        try:
            cur.execute("ALTER TABLE subscriptions ADD COLUMN subscribed_at DATETIME")
            con.commit()
        except Exception:
            pass  # 이미 존재하는 경우 무시
        cur.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                video_id TEXT,
                title TEXT,
                description TEXT,
                published_at DATETIME,
                thumbnail_url TEXT,
                ai_summary TEXT,
                FOREIGN KEY (subscription_id) REFERENCES subscriptions (id)
            )
        """)
        con.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error("Failed to initialize db: %s", e)
    finally:
        try:
            next(gen)
        except StopIteration:
            pass
