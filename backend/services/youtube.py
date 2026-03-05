from googleapiclient.discovery import build
import datetime

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
                    "thumbnail_url": snippet["thumbnails"]["default"]["url"]
                })
            request = self.youtube.subscriptions().list_next(request, response)
        return subs

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
