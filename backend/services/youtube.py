import logging
from googleapiclient.discovery import build
import datetime

logger = logging.getLogger(__name__)

class YouTubeService:
    def __init__(self, credentials):
        self.youtube = build('youtube', 'v3', credentials=credentials)

    def get_subscriptions(self):
        subs = []
        request = self.youtube.subscriptions().list(
            part="snippet",
            mine=True,
            maxResults=50
        )
        while request is not None:
            response = request.execute()
            for item in response.get("items", []):
                snippet = item["snippet"]
                subs.append({
                    "channel_id": snippet["resourceId"]["channelId"],
                    "title": snippet["title"],
                    "description": snippet["description"],
                    "thumbnail_url": snippet["thumbnails"]["default"]["url"],
                    "subscribed_at": snippet.get("publishedAt"),
                })
            request = self.youtube.subscriptions().list_next(request, response)
        return subs

    def unsubscribe_channel(self, channel_id: str) -> bool:
        """채널 구독 취소. subscriptions.list로 리소스 ID 조회 후 delete."""
        request = self.youtube.subscriptions().list(
            part="id",
            mine=True,
            forChannelId=channel_id,
            maxResults=1,
        )
        response = request.execute()
        items = response.get("items", [])
        if not items:
            return False
        subscription_resource_id = items[0]["id"]
        self.youtube.subscriptions().delete(id=subscription_resource_id).execute()
        return True

    def get_recent_videos_for_channel(self, channel_id: str, days: int = 3):
        """playlistItems.list 사용 (1 unit) — search.list (100 units) 대신 사용"""
        uploads_playlist_id = "UU" + channel_id[2:]  # UCxxx → UUxxx
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
        try:
            request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=10,
            )
            response = request.execute()
        except Exception as e:
            logger.warning("채널 %s 플레이리스트 조회 실패: %s", channel_id, e)
            return []

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            published_at = snippet.get("publishedAt", "")
            try:
                pub_dt = datetime.datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
            except Exception:
                continue
            video_id = (
                item.get("contentDetails", {}).get("videoId")
                or snippet.get("resourceId", {}).get("videoId")
            )
            if not video_id:
                continue
            videos.append({
                "video_id": video_id,
                "title": snippet["title"],
                "description": snippet.get("description", ""),
                "published_at": published_at,
                "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url")
                    or snippet.get("thumbnails", {}).get("default", {}).get("url"),
            })
        return videos

    def get_recent_videos(self, channel_id, days=7):
        # 7일 전의 날짜 계산 (RFC 3339 형식)
        seven_days_ago = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat().replace("+00:00", "Z")
        
        request = self.youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=10,
            order="date",
            publishedAfter=seven_days_ago,
            type="video"
        )
        response = request.execute()
        
        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": snippet["title"],
                "description": snippet["description"],
                "published_at": snippet["publishedAt"],
                "thumbnail_url": snippet["thumbnails"]["default"]["url"]
            })
        return videos
