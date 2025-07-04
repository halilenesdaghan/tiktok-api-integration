# app/services/tiktok_commercial_service.py

import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.config.settings import settings

class TikTokCommercialAPIService:
    """TikTok Commercial Content API servisi"""
    
    def __init__(self):
        self.base_url = "https://business-api.tiktok.com/open_api/v1.3"
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def get_video_insights(
        self, 
        access_token: str,
        video_ids: List[str],
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Video insights metriklerini al
        
        Args:
            access_token: TikTok access token
            video_ids: Video ID listesi (max 20)
            metrics: İstenen metrikler listesi
        """
        if not metrics:
            metrics = [
                "video_view_2s",
                "video_view_6s", 
                "video_view_15s",
                "video_watched_25p",
                "video_watched_50p",
                "video_watched_75p",
                "video_watched_100p",
                "average_video_play_time",
                "average_video_play_per_user",
                "likes",
                "comments",
                "shares",
                "profile_visits",
                "follows",
                "clicks_on_music_disc",
                "ix_video_views",  # Instant experience views
                "ix_video_view_rate"  # Instant experience view rate
            ]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/video/insights/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "video_ids": video_ids,
                    "metrics": metrics,
                    "dimensions": ["age", "gender", "country"]  # Demografi bilgileri
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Commercial API error: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def get_creator_insights(
        self,
        access_token: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """Hesap seviyesi insights"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/creator/insights/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json={
                    "start_date": start_date.strftime("%Y-%m-%d"),
                    "end_date": end_date.strftime("%Y-%m-%d"),
                    "metrics": [
                        "profile_views",
                        "followers_count",
                        "video_views",
                        "likes",
                        "comments",
                        "shares"
                    ]
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Creator insights error: {response.text}")
            
            return response.json()