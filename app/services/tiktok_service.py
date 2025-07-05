# app/services/tiktok_service.py

import httpx
from typing import Dict, Any, Optional
from app.config.settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential


class TikTokAPIService:
    """Service for interacting with TikTok API"""
    
    def __init__(self):
        self.base_url = "https://open.tiktokapis.com/v2"
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get TikTok user information"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/user/info/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                params={
                    "fields": "open_id,union_id,avatar_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count"
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"TikTok API error: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def get_user_videos(
        self, 
        access_token: str, 
        cursor: Optional[str] = None,
        max_count: int = 20
    ) -> Dict[str, Any]:
        """Get user's TikTok videos"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            body = {"max_count": max_count}
            if cursor:
                body["cursor"] = cursor
            
            response = await client.post(
                f"{self.base_url}/video/list/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code != 200:
                raise Exception(f"TikTok API error: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def get_video_query(
        self,
        access_token: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Query videos with filters"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            body = {
                "fields": "id,create_time,cover_image_url,share_url,video_description,duration,height,width,title,embed_html,embed_link,like_count,comment_count,share_count,view_count"
            }
            
            if filters:
                body.update(filters)
            
            response = await client.post(
                f"{self.base_url}/video/query/",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                },
                json=body
            )
            
            if response.status_code != 200:
                raise Exception(f"TikTok API error: {response.status_code} - {response.text}")
            
            return response.json()
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh TikTok access token"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://open.tiktokapis.com/v2/oauth/token/",
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data={
                    "client_key": settings.TIKTOK_CLIENT_KEY,
                    "client_secret": settings.TIKTOK_CLIENT_SECRET,
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Token refresh error: {response.status_code} - {response.text}")
            
            return response.json()