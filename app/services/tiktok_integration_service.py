# app/services/tiktok_integration_service.py

import httpx
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TikTokIntegrationService:
    """
    A service class for integrating with TikTok API to retrieve
    authorized user data and analytics.
    
    All methods are implemented as static methods that accept an authorized token
    as the first parameter and return JSON-decoded responses from the API.
    """
    
    BASE_URL = "https://open.tiktokapis.com/v2"
    TIMEOUT = httpx.Timeout(30.0, connect=10.0)
    
    @staticmethod
    async def _make_request(
        endpoint: str, 
        access_token: str, 
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Helper method to make API requests to TikTok API.
        
        Args:
            endpoint (str): The API endpoint to call
            access_token (str): The OAuth access token
            method (str): HTTP method (GET or POST)
            params (Dict[str, Any], optional): Query parameters
            json_data (Dict[str, Any], optional): JSON body for POST requests
            
        Returns:
            Dict[str, Any]: The JSON-decoded response
        """
        url = f"{TikTokIntegrationService.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=TikTokIntegrationService.TIMEOUT) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers, params=params)
                else:  # POST
                    response = await client.post(url, headers=headers, json=json_data)
                
                if response.status_code != 200:
                    logger.error(f"TikTok API error: {response.status_code} - {response.text}")
                    # Return empty data instead of raising exception
                    return {"data": {}, "error": response.text}
                
                return response.json()
                
        except Exception as e:
            logger.error(f"TikTok API request failed: {str(e)}")
            return {"data": {}, "error": str(e)}
    
    # -------------------------------------------------------------------------
    # Account Data Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    async def get_user_info(access_token: str) -> Dict[str, Any]:
        """
        Get comprehensive user information.
        
        Args:
            access_token (str): The OAuth access token
            
        Returns:
            Dict[str, Any]: User information including stats
        """
        params = {
            "fields": "open_id,union_id,avatar_url,avatar_url_100,avatar_large_url,display_name,bio_description,profile_deep_link,is_verified,follower_count,following_count,likes_count,video_count"
        }
        return await TikTokIntegrationService._make_request("/user/info/", access_token, params=params)
    
    @staticmethod
    async def get_follower_count(access_token: str) -> int:
        """
        Get the user's follower count.
        
        Args:
            access_token (str): The OAuth access token
            
        Returns:
            int: Follower count (0 if error)
        """
        result = await TikTokIntegrationService.get_user_info(access_token)
        return result.get("data", {}).get("user", {}).get("follower_count", 0)
    
    @staticmethod
    async def get_following_count(access_token: str) -> int:
        """
        Get the count of accounts the user follows.
        
        Args:
            access_token (str): The OAuth access token
            
        Returns:
            int: Following count (0 if error)
        """
        result = await TikTokIntegrationService.get_user_info(access_token)
        return result.get("data", {}).get("user", {}).get("following_count", 0)
    
    @staticmethod
    async def get_likes_count(access_token: str) -> int:
        """
        Get the total likes count across all videos.
        
        Args:
            access_token (str): The OAuth access token
            
        Returns:
            int: Total likes count (0 if error)
        """
        result = await TikTokIntegrationService.get_user_info(access_token)
        return result.get("data", {}).get("user", {}).get("likes_count", 0)
    
    @staticmethod
    async def get_video_count(access_token: str) -> int:
        """
        Get the total number of videos.
        
        Args:
            access_token (str): The OAuth access token
            
        Returns:
            int: Video count (0 if error)
        """
        result = await TikTokIntegrationService.get_user_info(access_token)
        return result.get("data", {}).get("user", {}).get("video_count", 0)
    
    # -------------------------------------------------------------------------
    # Video Data Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    async def get_video_list(
        access_token: str, 
        cursor: Optional[str] = None,
        max_count: int = 20
    ) -> Dict[str, Any]:
        """
        Get list of user's videos.
        
        Args:
            access_token (str): The OAuth access token
            cursor (str, optional): Pagination cursor
            max_count (int): Maximum videos to return (max 20)
            
        Returns:
            Dict[str, Any]: Video list with pagination info
        """
        body = {"max_count": min(max_count, 20)}
        if cursor:
            body["cursor"] = cursor
            
        return await TikTokIntegrationService._make_request(
            "/video/list/", 
            access_token, 
            method="POST",
            json_data=body
        )
    
    @staticmethod
    async def get_all_videos(access_token: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all videos using pagination (up to limit).
        
        Args:
            access_token (str): The OAuth access token
            limit (int): Maximum total videos to fetch
            
        Returns:
            List[Dict[str, Any]]: List of all videos
        """
        all_videos = []
        cursor = None
        
        while len(all_videos) < limit:
            result = await TikTokIntegrationService.get_video_list(
                access_token, 
                cursor, 
                min(20, limit - len(all_videos))
            )
            
            videos = result.get("data", {}).get("videos", [])
            if not videos:
                break
                
            all_videos.extend(videos)
            
            if not result.get("data", {}).get("has_more", False):
                break
                
            cursor = result.get("data", {}).get("cursor")
            
        return all_videos[:limit]
    
    @staticmethod
    async def get_video_stats(access_token: str, video_id: str) -> Dict[str, Any]:
        """
        Get statistics for a specific video.
        
        Args:
            access_token (str): The OAuth access token
            video_id (str): Video ID
            
        Returns:
            Dict[str, Any]: Video statistics
        """
        # Query specific video
        body = {
            "filters": {
                "video_ids": [video_id]
            },
            "fields": "id,create_time,video_description,duration,like_count,comment_count,share_count,view_count"
        }
        
        result = await TikTokIntegrationService._make_request(
            "/video/query/",
            access_token,
            method="POST",
            json_data=body
        )
        
        videos = result.get("data", {}).get("videos", [])
        if videos:
            return videos[0]
        return {}
    
    # -------------------------------------------------------------------------
    # Analytics Aggregation Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    async def get_total_video_stats(access_token: str) -> Dict[str, int]:
        """
        Get aggregated statistics across all videos.
        
        Returns:
            Dict[str, int]: Total likes, comments, shares, views
        """
        videos = await TikTokIntegrationService.get_all_videos(access_token)
        
        total_stats = {
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "total_views": 0,
            "video_count": len(videos)
        }
        
        for video in videos:
            total_stats["total_likes"] += video.get("like_count", 0)
            total_stats["total_comments"] += video.get("comment_count", 0)
            total_stats["total_shares"] += video.get("share_count", 0)
            total_stats["total_views"] += video.get("view_count", 0)
            
        return total_stats
    
    @staticmethod
    async def get_engagement_metrics(access_token: str) -> Dict[str, Any]:
        """
        Calculate engagement metrics from available data.
        
        Returns comprehensive engagement data including:
        - Total and average engagement rates
        - Top performing videos
        - Engagement breakdown
        """
        # Get user info and videos
        user_info = await TikTokIntegrationService.get_user_info(access_token)
        videos = await TikTokIntegrationService.get_all_videos(access_token)
        
        # Extract user data
        user_data = user_info.get("data", {}).get("user", {})
        
        # Calculate totals
        total_views = sum(v.get("view_count", 0) for v in videos)
        total_likes = sum(v.get("like_count", 0) for v in videos)
        total_comments = sum(v.get("comment_count", 0) for v in videos)
        total_shares = sum(v.get("share_count", 0) for v in videos)
        
        # Calculate engagement rate
        engagement_rate = 0
        if total_views > 0:
            engagement_rate = ((total_likes + total_comments + total_shares) / total_views) * 100
        
        # Find top videos
        top_videos = sorted(videos, key=lambda x: x.get("view_count", 0), reverse=True)[:5]
        
        return {
            "account_stats": {
                "follower_count": user_data.get("follower_count", 0),
                "following_count": user_data.get("following_count", 0),
                "total_likes_received": user_data.get("likes_count", 0),
                "video_count": user_data.get("video_count", 0)
            },
            "engagement_data": {
                "total_views": total_views,
                "total_likes": total_likes,
                "total_comments": total_comments,
                "total_shares": total_shares,
                "engagement_rate": round(engagement_rate, 2),
                "avg_views_per_video": round(total_views / len(videos), 0) if videos else 0,
                "avg_likes_per_video": round(total_likes / len(videos), 0) if videos else 0,
                "avg_comments_per_video": round(total_comments / len(videos), 0) if videos else 0,
                "avg_shares_per_video": round(total_shares / len(videos), 0) if videos else 0
            },
            "top_videos": [
                {
                    "id": v.get("id"),
                    "description": v.get("video_description", "")[:100],
                    "views": v.get("view_count", 0),
                    "likes": v.get("like_count", 0),
                    "comments": v.get("comment_count", 0),
                    "shares": v.get("share_count", 0),
                    "engagement_rate": round(
                        ((v.get("like_count", 0) + v.get("comment_count", 0) + v.get("share_count", 0)) / 
                         v.get("view_count", 1)) * 100, 2
                    ) if v.get("view_count", 0) > 0 else 0
                }
                for v in top_videos
            ],
            # Commercial API required fields (returning 0 as requested)
            "profile_visits": 0,
            "profile_visit_rate": 0,
            "music_clicks": 0,
            "instant_experience_view_time": 0,
            "instant_experience_view_rate": 0,
            "note": "Profile visits, music clicks, and instant experience data require TikTok Commercial API access"
        }
    
    # -------------------------------------------------------------------------
    # Time-based Analytics Methods
    # -------------------------------------------------------------------------
    
    @staticmethod
    async def get_recent_performance(
        access_token: str, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get performance metrics for recent videos.
        
        Args:
            access_token (str): The OAuth access token
            days (int): Number of days to look back
            
        Returns:
            Dict[str, Any]: Recent performance metrics
        """
        videos = await TikTokIntegrationService.get_all_videos(access_token)
        
        # Filter recent videos
        cutoff_timestamp = int((datetime.now() - timedelta(days=days)).timestamp())
        recent_videos = [
            v for v in videos 
            if v.get("create_time", 0) >= cutoff_timestamp
        ]
        
        if not recent_videos:
            return {
                "period_days": days,
                "video_count": 0,
                "total_views": 0,
                "total_engagement": 0,
                "avg_engagement_rate": 0
            }
        
        # Calculate metrics
        total_views = sum(v.get("view_count", 0) for v in recent_videos)
        total_likes = sum(v.get("like_count", 0) for v in recent_videos)
        total_comments = sum(v.get("comment_count", 0) for v in recent_videos)
        total_shares = sum(v.get("share_count", 0) for v in recent_videos)
        
        engagement_rate = 0
        if total_views > 0:
            engagement_rate = ((total_likes + total_comments + total_shares) / total_views) * 100
        
        return {
            "period_days": days,
            "video_count": len(recent_videos),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "total_engagement": total_likes + total_comments + total_shares,
            "avg_engagement_rate": round(engagement_rate, 2),
            "daily_avg_views": round(total_views / days, 0),
            "daily_avg_engagement": round((total_likes + total_comments + total_shares) / days, 0)
        }