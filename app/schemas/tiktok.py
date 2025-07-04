# app/schemas/tiktok.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime


# TikTok User Schemas
class TikTokUserInfo(BaseModel):
    open_id: str
    union_id: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    avatar_url_100: Optional[HttpUrl] = None
    avatar_large_url: Optional[HttpUrl] = None
    display_name: str
    bio_description: Optional[str] = None
    profile_deep_link: Optional[str] = None
    is_verified: bool = False
    follower_count: int = 0
    following_count: int = 0
    likes_count: int = 0
    video_count: int = 0


# TikTok Video Schemas
class TikTokVideo(BaseModel):
    id: str
    create_time: int
    cover_image_url: Optional[HttpUrl] = None
    share_url: HttpUrl
    video_description: Optional[str] = None
    duration: int = 0
    height: Optional[int] = None
    width: Optional[int] = None
    title: Optional[str] = None
    embed_html: Optional[str] = None
    embed_link: Optional[HttpUrl] = None
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    view_count: int = 0


class TikTokVideoList(BaseModel):
    videos: List[TikTokVideo]
    cursor: Optional[int] = None
    has_more: bool = False


# Analytics Schemas
class VideoAnalyticsCreate(BaseModel):
    video_id: str
    video_description: Optional[str] = None
    duration: Optional[int] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    cover_image_url: Optional[str] = None
    share_url: Optional[str] = None
    height: Optional[int] = None
    width: Optional[int] = None
    video_created_at: Optional[datetime] = None
    hashtags: Optional[List[str]] = []


class VideoAnalyticsResponse(VideoAnalyticsCreate):
    id: int
    user_id: int
    fetched_at: datetime
    engagement_rate: Optional[float] = None
    
    class Config:
        from_attributes = True


class EngagementMetrics(BaseModel):
    total_videos: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    avg_engagement_rate: float = 0.0
    avg_views_per_video: float = 0.0
    most_viewed_video: Optional[Dict[str, Any]] = None
    best_engagement_video: Optional[Dict[str, Any]] = None


class GrowthTrends(BaseModel):
    weekly_view_trend: float = 0.0
    weekly_engagement_trend: float = 0.0
    posting_frequency: float = 0.0
    best_performing_week: Optional[str] = None


class AccountAnalytics(BaseModel):
    user_info: TikTokUserInfo
    engagement_metrics: EngagementMetrics
    growth_trends: Optional[GrowthTrends] = None
    recent_videos: List[TikTokVideo] = []
    analytics_date: datetime = Field(default_factory=datetime.now)