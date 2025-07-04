# app/api/v1/endpoints/tiktok.py
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.config.database import get_db
from app.models.user import User
from app.models.token import Token
from app.models.analytics import VideoAnalytics
from app.schemas.tiktok import (
    TikTokUserInfo, TikTokVideo, TikTokVideoList,
    VideoAnalyticsCreate, VideoAnalyticsResponse,
    AccountAnalytics
)
from app.services.tiktok_service import TikTokAPIService
from app.services.analytics_service import AnalyticsService
from app.core.security import TokenEncryption
from app.api.v1.endpoints.auth import get_current_user
from app.config.settings import settings

from app.services.tiktok_commercial_service import TikTokCommercialAPIService
from app.models.analytics import VideoInsights

router = APIRouter()
tiktok_service = TikTokAPIService()
analytics_service = AnalyticsService()
token_encryption = TokenEncryption("L8poBUJPRWeYJudhwR9k_j9u7xyEkOts0j1kskJdQaA=")
commercial_service = TikTokCommercialAPIService()


async def get_tiktok_token(user: User, db: AsyncSession) -> str:
    """Kullanıcının TikTok access token'ını al"""
    result = await db.execute(
        select(Token).filter(
            Token.user_id == user.id,
            Token.token_type == "tiktok",
            Token.is_active == True
        )
    )
    token = result.scalar_one_or_none()
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TikTok account not connected"
        )
    
    # Token süresini kontrol et
    if token.expires_at and token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="TikTok token expired. Please reconnect your account."
        )
    
    # Token'ı decrypt et
    return token_encryption.decrypt(token.access_token)


@router.get("/user/info", response_model=TikTokUserInfo)
async def get_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """TikTok kullanıcı bilgilerini al"""
    access_token = await get_tiktok_token(current_user, db)
    
    try:
        user_data = await tiktok_service.get_user_info(access_token)
        
        # Kullanıcı bilgilerini veritabanında güncelle
        current_user.tiktok_display_name = user_data.get("data", {}).get("user", {}).get("display_name")
        current_user.tiktok_avatar_url = user_data.get("data", {}).get("user", {}).get("avatar_url")
        current_user.tiktok_follower_count = user_data.get("data", {}).get("user", {}).get("follower_count", 0)
        current_user.tiktok_following_count = user_data.get("data", {}).get("user", {}).get("following_count", 0)
        current_user.tiktok_likes_count = user_data.get("data", {}).get("user", {}).get("likes_count", 0)
        current_user.tiktok_video_count = user_data.get("data", {}).get("user", {}).get("video_count", 0)
        
        await db.commit()
        
        # Response formatla
        user_info = user_data.get("data", {}).get("user", {})
        return TikTokUserInfo(**user_info)
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user info: {str(e)}"
        )


@router.get("/videos", response_model=TikTokVideoList)
async def get_user_videos(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    max_count: int = Query(20, ge=1, le=100, description="Maximum number of videos to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Kullanıcının TikTok videolarını al"""
    access_token = await get_tiktok_token(current_user, db)
    
    try:
        video_data = await tiktok_service.get_user_videos(access_token, cursor)
        
        videos = []
        for video in video_data.get("data", {}).get("videos", []):
            videos.append(TikTokVideo(**video))
            
            # Video verilerini analytics tablosuna kaydet
            result = await db.execute(
                select(VideoAnalytics).filter(
                    VideoAnalytics.user_id == current_user.id,
                    VideoAnalytics.video_id == video["id"]
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                video_analytics = VideoAnalytics(
                    user_id=current_user.id,
                    video_id=video["id"],
                    video_description=video.get("video_description"),
                    duration=video.get("duration", 0),
                    view_count=video.get("view_count", 0),
                    like_count=video.get("like_count", 0),
                    comment_count=video.get("comment_count", 0),
                    share_count=video.get("share_count", 0),
                    cover_image_url=video.get("cover_image_url"),
                    share_url=video.get("share_url"),
                    height=video.get("height"),
                    width=video.get("width"),
                    video_created_at=datetime.fromtimestamp(video.get("create_time", 0))
                )
                db.add(video_analytics)
            else:
                # Metrikleri güncelle
                existing.view_count = video.get("view_count", 0)
                existing.like_count = video.get("like_count", 0)
                existing.comment_count = video.get("comment_count", 0)
                existing.share_count = video.get("share_count", 0)
        
        await db.commit()
        
        return TikTokVideoList(
            videos=videos[:max_count],
            cursor=video_data.get("data", {}).get("cursor"),
            has_more=video_data.get("data", {}).get("has_more", False)
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch videos: {str(e)}"
        )


@router.get("/videos/{video_id}", response_model=VideoAnalyticsResponse)
async def get_video_analytics(
    video_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Belirli bir video için analytics verilerini al"""
    result = await db.execute(
        select(VideoAnalytics).filter(
            VideoAnalytics.user_id == current_user.id,
            VideoAnalytics.video_id == video_id
        )
    )
    video_analytics = result.scalar_one_or_none()
    
    if not video_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video analytics not found"
        )
    
    # Engagement rate hesapla
    if video_analytics.view_count > 0:
        video_analytics.engagement_rate = (
            (video_analytics.like_count + 
             video_analytics.comment_count + 
             video_analytics.share_count) / 
            video_analytics.view_count * 100
        )
    
    return video_analytics


@router.post("/sync", response_model=dict)
async def sync_tiktok_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """TikTok verilerini senkronize et"""
    access_token = await get_tiktok_token(current_user, db)
    
    try:
        # Kullanıcı bilgilerini güncelle
        user_data = await tiktok_service.get_user_info(access_token)
        user_info = user_data.get("data", {}).get("user", {})
        
        current_user.tiktok_display_name = user_info.get("display_name")
        current_user.tiktok_avatar_url = user_info.get("avatar_url")
        current_user.tiktok_follower_count = user_info.get("follower_count", 0)
        current_user.tiktok_following_count = user_info.get("following_count", 0)
        current_user.tiktok_likes_count = user_info.get("likes_count", 0)
        current_user.tiktok_video_count = user_info.get("video_count", 0)
        
        # Videoları senkronize et
        video_count = 0
        cursor = None
        
        while True:
            video_data = await tiktok_service.get_user_videos(access_token, cursor)
            videos = video_data.get("data", {}).get("videos", [])
            
            for video in videos:
                video_count += 1
                
                # Video analytics kaydet/güncelle
                result = await db.execute(
                    select(VideoAnalytics).filter(
                        VideoAnalytics.user_id == current_user.id,
                        VideoAnalytics.video_id == video["id"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    video_analytics = VideoAnalytics(
                        user_id=current_user.id,
                        video_id=video["id"],
                        video_description=video.get("video_description"),
                        duration=video.get("duration", 0),
                        view_count=video.get("view_count", 0),
                        like_count=video.get("like_count", 0),
                        comment_count=video.get("comment_count", 0),
                        share_count=video.get("share_count", 0),
                        cover_image_url=video.get("cover_image_url"),
                        share_url=video.get("share_url"),
                        height=video.get("height"),
                        width=video.get("width"),
                        video_created_at=datetime.fromtimestamp(video.get("create_time", 0))
                    )
                    db.add(video_analytics)
                else:
                    existing.view_count = video.get("view_count", 0)
                    existing.like_count = video.get("like_count", 0)
                    existing.comment_count = video.get("comment_count", 0)
                    existing.share_count = video.get("share_count", 0)
            
            # Pagination
            if not video_data.get("data", {}).get("has_more", False):
                break
            
            cursor = video_data.get("data", {}).get("cursor")
            
            # Maksimum 100 video al
            if video_count >= 100:
                break
        
        await db.commit()
        
        return {
            "message": "Sync completed successfully",
            "user_synced": True,
            "videos_synced": video_count
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


@router.get("/analytics/summary", response_model=AccountAnalytics)
async def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Hesap analytics özeti"""
    # Video verilerini al
    result = await db.execute(
        select(VideoAnalytics).filter(
            VideoAnalytics.user_id == current_user.id
        )
    )
    videos = result.scalars().all()
    
    if not videos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No video data found. Please sync your account first."
        )
    
    # Video verilerini dict listesine çevir
    video_data = []
    for video in videos:
        video_data.append({
            "id": video.video_id,
            "create_time": int(video.video_created_at.timestamp()) if video.video_created_at else 0,
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "share_count": video.share_count,
            "video_description": video.video_description,
            "duration": video.duration,
            "cover_image_url": video.cover_image_url,
            "share_url": video.share_url
        })
    
    # Engagement metrikleri hesapla
    engagement_metrics = analytics_service.calculate_engagement_metrics(video_data)
    
    # Growth trends hesapla
    growth_trends = analytics_service.calculate_growth_trends(video_data)
    
    # Son 10 video
    recent_videos = sorted(video_data, key=lambda x: x["create_time"], reverse=True)[:10]
    
    # TikTok user info
    user_info = TikTokUserInfo(
        open_id=current_user.tiktok_open_id or "",
        display_name=current_user.tiktok_display_name or current_user.username,
        avatar_url=current_user.tiktok_avatar_url,
        follower_count=current_user.tiktok_follower_count or 0,
        following_count=current_user.tiktok_following_count or 0,
        likes_count=current_user.tiktok_likes_count or 0,
        video_count=current_user.tiktok_video_count or 0
    )
    
    return AccountAnalytics(
        user_info=user_info,
        engagement_metrics=engagement_metrics,
        growth_trends=growth_trends,
        recent_videos=[TikTokVideo(**v) for v in recent_videos]
    )

@router.post("/videos/fetch-insights")
async def fetch_video_insights(
    video_ids: List[str] = Query(..., max_items=20, description="Video ID listesi"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Video insights metriklerini Commercial API'den çek"""
    access_token = await get_tiktok_token(current_user, db)
    
    try:
        # Commercial API'den insights al
        insights_data = await commercial_service.get_video_insights(
            access_token=access_token,
            video_ids=video_ids
        )
        
        # Her video için insights kaydet
        saved_count = 0
        for video_data in insights_data.get("data", {}).get("videos", []):
            video_id = video_data["video_id"]
            
            # VideoAnalytics kaydını bul
            result = await db.execute(
                select(VideoAnalytics).filter(
                    VideoAnalytics.user_id == current_user.id,
                    VideoAnalytics.video_id == video_id
                )
            )
            video_analytics = result.scalar_one_or_none()
            
            if video_analytics:
                # Mevcut insights'ı kontrol et
                result = await db.execute(
                    select(VideoInsights).filter(
                        VideoInsights.video_analytics_id == video_analytics.id
                    )
                )
                video_insights = result.scalar_one_or_none()
                
                if not video_insights:
                    video_insights = VideoInsights(video_analytics_id=video_analytics.id)
                    db.add(video_insights)
                
                # Metrikleri güncelle
                metrics = video_data.get("metrics", {})
                video_insights.view_count_2s = metrics.get("video_view_2s", 0)
                video_insights.view_count_6s = metrics.get("video_view_6s", 0)
                video_insights.view_count_15s = metrics.get("video_view_15s", 0)
                video_insights.retention_rate_25 = metrics.get("video_watched_25p", 0)
                video_insights.retention_rate_50 = metrics.get("video_watched_50p", 0)
                video_insights.retention_rate_75 = metrics.get("video_watched_75p", 0)
                video_insights.retention_rate_100 = metrics.get("video_watched_100p", 0)
                video_insights.avg_watch_time = metrics.get("average_video_play_time", 0)
                video_insights.avg_watch_time_per_user = metrics.get("average_video_play_per_user", 0)
                video_insights.profile_visits = metrics.get("profile_visits", 0)
                video_insights.follow_count = metrics.get("follows", 0)
                video_insights.music_clicks = metrics.get("clicks_on_music_disc", 0)
                video_insights.instant_exp_view_time = metrics.get("ix_video_views", 0)
                video_insights.instant_exp_view_rate = metrics.get("ix_video_view_rate", 0)
                video_insights.demographics = video_data.get("demographics", {})
                
                saved_count += 1
        
        await db.commit()
        
        return {
            "message": f"Insights fetched for {saved_count} videos",
            "total_requested": len(video_ids),
            "saved_count": saved_count
        }
        
    except Exception as e:
        await db.rollback()
        # Commercial API erişimi yoksa alternatif çözüm
        if "403" in str(e) or "permission" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Commercial API access required. Please apply for TikTok Commercial API access."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch insights: {str(e)}"
        )
    
    @router.get("/videos/{video_id}/detailed-insights")
    async def get_detailed_video_insights(
        video_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """Detaylı video insights'ı getir"""
        # Video analytics'i bul
        result = await db.execute(
            select(VideoAnalytics).filter(
                VideoAnalytics.user_id == current_user.id,
                VideoAnalytics.video_id == video_id
        )
    )
    video_analytics = result.scalar_one_or_none()
    
    if not video_analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video not found"
        )
    
    # Insights'ı al
    result = await db.execute(
        select(VideoInsights).filter(
            VideoInsights.video_analytics_id == video_analytics.id
        )
    )
    insights = result.scalar_one_or_none()
    
    if not insights:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video insights not found. Please fetch insights first."
        )
    
    return {
        "video_id": video_id,
        "basic_metrics": {
            "views": video_analytics.view_count,
            "likes": video_analytics.like_count,
            "comments": video_analytics.comment_count,
            "shares": video_analytics.share_count
        },
        "view_metrics": {
            "2s_views": insights.view_count_2s,
            "6s_views": insights.view_count_6s,
            "15s_views": insights.view_count_15s
        },
        "retention_rates": {
            "25_percent": f"{insights.retention_rate_25}%",
            "50_percent": f"{insights.retention_rate_50}%",
            "75_percent": f"{insights.retention_rate_75}%",
            "100_percent": f"{insights.retention_rate_100}%"
        },
        "watch_time": {
            "average_watch_time": f"{insights.avg_watch_time} seconds",
            "average_per_user": f"{insights.avg_watch_time_per_user} seconds"
        },
        "engagement": {
            "profile_visits": insights.profile_visits,
            "follows": insights.follow_count,
            "music_clicks": insights.music_clicks
        },
        "instant_experience": {
            "view_time": insights.instant_exp_view_time,
            "view_rate": f"{insights.instant_exp_view_rate}%"
        },
        "demographics": insights.demographics,
        "last_updated": insights.fetched_at.isoformat()
    }
