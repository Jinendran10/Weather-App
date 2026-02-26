"""
YouTube Data API v3 integration service.
Returns travel / location videos for a given place.
"""

import httpx
from typing import List, Dict, Any
from app.config import settings


class YouTubeService:

    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    async def search_location_videos(
        self,
        location_name: str,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Search YouTube for videos about the given location.
        Returns a list of video metadata dicts.
        """
        if not settings.YOUTUBE_API_KEY:
            return self._mock_videos(location_name)

        query = f"{location_name} travel weather"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "order": "relevance",
            "key": settings.YOUTUBE_API_KEY,
            "videoEmbeddable": "true",
            "safeSearch": "strict",
        }
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.SEARCH_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                return []
            raise

        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            vid_id = item.get("id", {}).get("videoId", "")
            videos.append(
                {
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "thumbnail_url": snippet.get("thumbnails", {})
                    .get("high", {})
                    .get("url", ""),
                    "channel_title": snippet.get("channelTitle", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "youtube_url": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )
        return videos

    def _mock_videos(self, location_name: str) -> List[Dict[str, Any]]:
        """
        Return placeholder data when no YouTube API key is configured.
        Useful for development / demo purposes.
        """
        return [
            {
                "video_id": "dQw4w9WgXcQ",
                "title": f"Exploring {location_name} - Travel Guide",
                "description": f"A beautiful tour of {location_name}.",
                "thumbnail_url": "https://img.youtube.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                "channel_title": "Demo Travel Channel",
                "published_at": "2024-01-01T00:00:00Z",
                "youtube_url": f"https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            }
        ]


youtube_service = YouTubeService()
