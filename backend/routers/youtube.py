import os
import json
import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException
from google.oauth2.credentials import Credentials
import database
from auth.jwt import get_current_user
from services.youtube import YouTubeService
from services.gemini import categorize_channels, summarize_videos

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/youtube", tags=["youtube"])


# ── 헬퍼 함수 ──────────────────────────────────────────────────────────────

def get_user_row(cur, user_id: int):
    cur.execute("SELECT id, access_token, refresh_token FROM users WHERE id = ?", (user_id,))
    return cur.fetchone()


def build_credentials(access_token: str, refresh_token: str | None) -> Credentials:
    """H-3: Credentials 생성 헬퍼 — 중복 코드 제거"""
    return Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )


# ── 조회 엔드포인트 (GET) ───────────────────────────────────────────────────

@router.get("/categories")
def get_categories(user_id: int = Depends(get_current_user), db=Depends(database.get_db)):
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="User not found")
    cur.execute(
        "SELECT DISTINCT category FROM subscriptions WHERE user_id = ? ORDER BY category",
        (user_id,),
    )
    categories = [row[0] for row in cur.fetchall()]
    return {"categories": categories}


@router.get("/subscriptions")
def get_subscriptions(user_id: int = Depends(get_current_user), category: str = "all", db=Depends(database.get_db)):
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE id = ?", (user_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    # 3일 이내 영상만 표시
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=3)).isoformat()

    video_subquery = """
        SELECT subscription_id, video_id, title, published_at, thumbnail_url, ai_summary,
               ROW_NUMBER() OVER (PARTITION BY subscription_id ORDER BY published_at DESC) AS rn
        FROM videos
        WHERE published_at >= ?
    """

    if category == "all":
        cur.execute(
            f"""
            SELECT s.id, s.channel_id, s.channel_title, s.thumbnail_url, s.category,
                   v.video_id, v.title, v.published_at, v.thumbnail_url, v.ai_summary
            FROM subscriptions s
            LEFT JOIN ({video_subquery}) v ON v.subscription_id = s.id AND v.rn <= 5
            WHERE s.user_id = ?
            ORDER BY s.category, s.channel_title, v.published_at DESC
            """,
            (cutoff, user_id),
        )
    else:
        # 부모 카테고리 prefix 매칭 지원 (예: "IT/Tech" → "IT/Tech > AI" 포함)
        cur.execute(
            f"""
            SELECT s.id, s.channel_id, s.channel_title, s.thumbnail_url, s.category,
                   v.video_id, v.title, v.published_at, v.thumbnail_url, v.ai_summary
            FROM subscriptions s
            LEFT JOIN ({video_subquery}) v ON v.subscription_id = s.id AND v.rn <= 5
            WHERE s.user_id = ? AND (s.category = ? OR s.category LIKE ?)
            ORDER BY s.channel_title, v.published_at DESC
            """,
            (cutoff, user_id, category, f"{category} > %"),
        )

    rows = cur.fetchall()

    # 구독별로 그룹화
    subs: dict[int, dict] = {}
    for row in rows:
        sub_id = row[0]
        if sub_id not in subs:
            subs[sub_id] = {
                "id": row[0],
                "channel_id": row[1],
                "channel_title": row[2],
                "thumbnail_url": row[3],
                "category": row[4],
                "videos": [],
            }
        if row[5]:  # video_id가 있을 때만 추가
            subs[sub_id]["videos"].append({
                "video_id": row[5],
                "title": row[6],
                "published_at": row[7],
                "thumbnail_url": row[8],
                "ai_summary": row[9],
            })

    return {"subscriptions": list(subs.values())}


# ── 변경 엔드포인트 (POST) ─────────────────────────────────────────────────

@router.post("/sync-subscriptions")
def sync_subscriptions(user_id: int = Depends(get_current_user), db=Depends(database.get_db)):
    """H-1: GET → POST (DB 쓰기 작업)"""
    cur = db.cursor()
    user_row = get_user_row(cur, user_id)

    if not user_row:
        raise HTTPException(status_code=404, detail="User not found")

    u_id, access_token, refresh_token = user_row

    if not access_token:
        raise HTTPException(status_code=400, detail="User has no Google credentials.")

    creds = build_credentials(access_token, refresh_token)
    youtube_service = YouTubeService(credentials=creds)
    subs = youtube_service.get_subscriptions()

    if not subs:
        return {"status": "success", "message": "No subscriptions found.", "synced_count": 0}

    try:
        # channel_id -> category 딕셔너리 직접 반환
        cat_map = categorize_channels(subs)
        logger.info("Gemini 카테고리 매핑 완료: %d개", len(cat_map))
    except Exception as e:
        logger.error("Gemini 카테고리 분류 오류: %s", e)
        cat_map = {}

    for sub in subs:
        cur.execute(
            "SELECT id, category FROM subscriptions WHERE user_id = ? AND channel_id = ?",
            (u_id, sub["channel_id"]),
        )
        existing = cur.fetchone()
        new_category = cat_map.get(sub["channel_id"])

        if existing:
            sub_id, current_category = existing[0], existing[1]
            # Gemini가 유의미한 카테고리를 반환한 경우에만 덮어씀
            update_category = new_category if new_category else current_category
            cur.execute(
                """
                UPDATE subscriptions
                SET channel_title = ?, channel_description = ?, thumbnail_url = ?, category = ?
                WHERE id = ?
                """,
                (sub["title"], sub["description"], sub["thumbnail_url"], update_category, sub_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO subscriptions (user_id, channel_id, channel_title, channel_description, thumbnail_url, category)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (u_id, sub["channel_id"], sub["title"], sub["description"], sub["thumbnail_url"], new_category or "Uncategorized"),
            )

    db.commit()

    # 각 채널의 최근 3일 영상 저장 (playlistItems.list — 1 unit/채널)
    synced_videos = 0
    for sub in subs:
        cur.execute(
            "SELECT id FROM subscriptions WHERE user_id = ? AND channel_id = ?",
            (u_id, sub["channel_id"]),
        )
        sub_row = cur.fetchone()
        if not sub_row:
            continue
        sub_id = sub_row[0]
        try:
            videos = youtube_service.get_recent_videos_for_channel(sub["channel_id"], days=3)
            for v in videos:
                cur.execute("SELECT id FROM videos WHERE video_id = ?", (v["video_id"],))
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO videos (subscription_id, video_id, title, description, published_at, thumbnail_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (sub_id, v["video_id"], v["title"], v["description"], v["published_at"], v["thumbnail_url"]),
                    )
                    synced_videos += 1
        except Exception as e:
            logger.warning("채널 %s 영상 조회 실패: %s", sub["channel_id"], e)

    db.commit()
    return {"status": "success", "synced_count": len(subs), "synced_videos": synced_videos}


@router.post("/summarize-recent")
def summarize_recent(channel_id: str, user_id: int = Depends(get_current_user), db=Depends(database.get_db)):
    """H-1: GET → POST (외부 API 호출 + DB 쓰기)"""
    cur = db.cursor()
    user_row = get_user_row(cur, user_id)

    if not user_row or not user_row[1]:
        raise HTTPException(status_code=400, detail="User not found or missing credentials.")

    u_id, access_token, refresh_token = user_row

    # 해당 채널이 이 유저의 구독인지 검증
    cur.execute(
        "SELECT id FROM subscriptions WHERE user_id = ? AND channel_id = ?",
        (u_id, channel_id),
    )
    sub_row = cur.fetchone()
    if not sub_row:
        raise HTTPException(status_code=403, detail="Channel not in user's subscriptions.")

    creds = build_credentials(access_token, refresh_token)
    youtube_service = YouTubeService(credentials=creds)
    videos = youtube_service.get_recent_videos(channel_id=channel_id, days=7)

    if not videos:
        return {"status": "success", "summary": "최근 7일간 업로드된 영상이 없습니다.", "videos": []}

    summary_text = summarize_videos(videos)
    sub_id = sub_row[0]

    for v in videos:
        cur.execute("SELECT id FROM videos WHERE video_id = ?", (v["video_id"],))
        existing_v = cur.fetchone()

        try:
            pub_date = datetime.datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
        except Exception:
            pub_date = datetime.datetime.now(datetime.timezone.utc)

        if not existing_v:
            cur.execute(
                """
                INSERT INTO videos (subscription_id, video_id, title, description, published_at, thumbnail_url, ai_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (sub_id, v["video_id"], v["title"], v["description"], pub_date.isoformat(), v["thumbnail_url"], summary_text),
            )
        else:
            cur.execute(
                "UPDATE videos SET ai_summary = ? WHERE video_id = ?",
                (summary_text, v["video_id"]),
            )

    db.commit()
    return {"status": "success", "summary": summary_text, "videos": videos}
