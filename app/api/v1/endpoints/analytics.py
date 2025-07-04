# app/api/v1/endpoints/analytics.py
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, and_
from sqlalchemy.future import select

from app.config.database import get_db
from app.models.user import User
from app.models.analytics import Analytics, VideoAnalytics
from app.schemas.tiktok import EngagementMetrics, GrowthTrends
from app.services.analytics_service import AnalyticsService
from app.api.v1.endpoints.auth import get_current_user

router = APIRouter()
analytics_service = AnalyticsService()


@router.get("/engagement", response_model=EngagementMetrics)
async def get_engagement_metrics(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Engagement metriklerini hesapla"""
    # Belirtilen süredeki videoları al
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(VideoAnalytics).filter(
            VideoAnalytics.user_id == current_user.id,
            VideoAnalytics.video_created_at >= start_date
        )
    )
    videos = result.scalars().all()
    
    if not videos:
        return EngagementMetrics()
    
    # Video verilerini dict listesine çevir
    video_data = []
    for video in videos:
        video_data.append({
            "id": video.video_id,
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "share_count": video.share_count
        })
    
    return analytics_service.calculate_engagement_metrics(video_data)


@router.get("/trends", response_model=GrowthTrends)
async def get_growth_trends(
    days: int = Query(90, ge=7, le=365, description="Number of days to analyze"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Büyüme trendlerini analiz et"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(VideoAnalytics).filter(
            VideoAnalytics.user_id == current_user.id,
            VideoAnalytics.video_created_at >= start_date
        )
    )
    videos = result.scalars().all()
    
    if not videos:
        return GrowthTrends()
    
    # Video verilerini dict listesine çevir
    video_data = []
    for video in videos:
        video_data.append({
            "id": video.video_id,
            "create_time": int(video.video_created_at.timestamp()),
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "share_count": video.share_count
        })
    
    return analytics_service.calculate_growth_trends(video_data)


@router.get("/performance/daily")
async def get_daily_performance(
    days: int = Query(7, ge=1, le=30, description="Number of days to show"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Günlük performans verileri"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Günlük video sayısı ve toplam metrikler
    result = await db.execute(
        select(
            func.date(VideoAnalytics.video_created_at).label("date"),
            func.count(VideoAnalytics.id).label("video_count"),
            func.sum(VideoAnalytics.view_count).label("total_views"),
            func.sum(VideoAnalytics.like_count).label("total_likes"),
            func.sum(VideoAnalytics.comment_count).label("total_comments"),
            func.sum(VideoAnalytics.share_count).label("total_shares")
        ).filter(
            VideoAnalytics.user_id == current_user.id,
            VideoAnalytics.video_created_at >= start_date
        ).group_by(
            func.date(VideoAnalytics.video_created_at)
        ).order_by(
            func.date(VideoAnalytics.video_created_at)
        )
    )
    daily_stats = result.all()
    
    result_data = []
    for stat in daily_stats:
        engagement_rate = 0
        if stat.total_views and stat.total_views > 0:
            engagement_rate = (
                (stat.total_likes + stat.total_comments + stat.total_shares) / 
                stat.total_views * 100
            )
        
        result_data.append({
            "date": stat.date.isoformat(),
            "video_count": stat.video_count,
            "total_views": stat.total_views or 0,
            "total_likes": stat.total_likes or 0,
            "total_comments": stat.total_comments or 0,
            "total_shares": stat.total_shares or 0,
            "engagement_rate": round(engagement_rate, 2)
        })
    
    return result_data


@router.get("/top-videos")
async def get_top_videos(
    metric: str = Query("views", regex="^(views|likes|comments|shares|engagement)$"),
    limit: int = Query(10, ge=1, le=50),
    days: Optional[int] = Query(None, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """En iyi performans gösteren videoları getir"""
    query = select(VideoAnalytics).filter(
        VideoAnalytics.user_id == current_user.id
    )
    
    # Tarih filtresi
    if days:
        start_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(VideoAnalytics.video_created_at >= start_date)
    
    # Metriğe göre sırala
    if metric == "views":
        query = query.order_by(VideoAnalytics.view_count.desc())
    elif metric == "likes":
        query = query.order_by(VideoAnalytics.like_count.desc())
    elif metric == "comments":
        query = query.order_by(VideoAnalytics.comment_count.desc())
    elif metric == "shares":
        query = query.order_by(VideoAnalytics.share_count.desc())
    elif metric == "engagement":
        # Engagement rate'e göre sırala
        from sqlalchemy import case
        engagement_rate = case(
            (VideoAnalytics.view_count > 0, 
             (VideoAnalytics.like_count + VideoAnalytics.comment_count + VideoAnalytics.share_count) * 100.0 / VideoAnalytics.view_count),
            else_=0
        )
        query = query.order_by(engagement_rate.desc())
    
    result = await db.execute(query.limit(limit))
    videos = result.scalars().all()
    
    result_data = []
    for video in videos:
        engagement_rate = 0
        if video.view_count > 0:
            engagement_rate = (
                (video.like_count + video.comment_count + video.share_count) / 
                video.view_count * 100
            )
        
        result_data.append({
            "video_id": video.video_id,
            "description": video.video_description,
            "created_at": video.video_created_at.isoformat() if video.video_created_at else None,
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "share_count": video.share_count,
            "engagement_rate": round(engagement_rate, 2),
            "share_url": video.share_url,
            "cover_image_url": video.cover_image_url
        })
    
    return result_data


@router.get("/hashtag-performance")
async def get_hashtag_performance(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Hashtag performans analizi"""
    result = await db.execute(
        select(VideoAnalytics).filter(
            VideoAnalytics.user_id == current_user.id,
            VideoAnalytics.hashtags.isnot(None)
        )
    )
    videos = result.scalars().all()
    
    hashtag_stats = {}
    
    for video in videos:
        if video.hashtags:
            for hashtag in video.hashtags:
                if hashtag not in hashtag_stats:
                    hashtag_stats[hashtag] = {
                        "count": 0,
                        "total_views": 0,
                        "total_likes": 0,
                        "total_comments": 0,
                        "total_shares": 0
                    }
                
                hashtag_stats[hashtag]["count"] += 1
                hashtag_stats[hashtag]["total_views"] += video.view_count
                hashtag_stats[hashtag]["total_likes"] += video.like_count
                hashtag_stats[hashtag]["total_comments"] += video.comment_count
                hashtag_stats[hashtag]["total_shares"] += video.share_count
    
    # Ortalama metrikleri hesapla ve sırala
    result_data = []
    for hashtag, stats in hashtag_stats.items():
        avg_views = stats["total_views"] / stats["count"] if stats["count"] > 0 else 0
        avg_engagement = (
            (stats["total_likes"] + stats["total_comments"] + stats["total_shares"]) / 
            stats["total_views"] * 100
        ) if stats["total_views"] > 0 else 0
        
        result_data.append({
            "hashtag": hashtag,
            "usage_count": stats["count"],
            "avg_views": round(avg_views, 0),
            "avg_engagement_rate": round(avg_engagement, 2),
            "total_views": stats["total_views"],
            "total_likes": stats["total_likes"]
        })
    
    # En yüksek ortalama görüntülemeye göre sırala
    result_data.sort(key=lambda x: x["avg_views"], reverse=True)
    
    return result_data[:limit]


@router.get("/recommendations")
async def get_recommendations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """İçerik üreticisi için öneriler"""
    # Son 30 günün verilerini al
    start_date = datetime.utcnow() - timedelta(days=30)
    
    result = await db.execute(
        select(VideoAnalytics).filter(
            VideoAnalytics.user_id == current_user.id,
            VideoAnalytics.video_created_at >= start_date
        )
    )
    videos = result.scalars().all()
    
    if not videos:
        return {
            "recommendations": [
                "Henüz yeterli veri yok. Lütfen hesabınızı senkronize edin ve birkaç video paylaşın."
            ]
        }
    
    recommendations = []
    
    # Ortalama engagement rate hesapla
    total_engagement = sum(
        (v.like_count + v.comment_count + v.share_count) / v.view_count * 100 
        if v.view_count > 0 else 0 
        for v in videos
    )
    avg_engagement = total_engagement / len(videos)
    
    # Öneriler
    if avg_engagement < 5:
        recommendations.append(
            "Engagement oranınız düşük (%{:.1f}). Takipçilerinizle daha fazla etkileşim kurmanız önerilir.".format(avg_engagement)
        )
    
    # Video sayısı analizi
    if len(videos) < 10:
        recommendations.append(
            "Son 30 günde sadece {} video paylaşmışsınız. Daha sık içerik paylaşımı yapmanız önerilir.".format(len(videos))
        )
    
    # En iyi performans gösteren video zamanları
    best_hours = {}
    for video in videos:
        if video.video_created_at:
            hour = video.video_created_at.hour
            if hour not in best_hours:
                best_hours[hour] = {"count": 0, "total_views": 0}
            best_hours[hour]["count"] += 1
            best_hours[hour]["total_views"] += video.view_count
    
    if best_hours:
        best_hour = max(best_hours.items(), key=lambda x: x[1]["total_views"] / x[1]["count"])[0]
        recommendations.append(
            f"En iyi performans gösteren paylaşım saatiniz: {best_hour}:00 - {best_hour+1}:00"
        )
    
    # Hashtag önerileri
    if any(v.hashtags for v in videos):
        recommendations.append(
            "Hashtag kullanımınız iyi. En popüler hashtaglerinizi analiz edin ve benzer içeriklerde kullanın."
        )
    else:
        recommendations.append(
            "Videolarınızda hashtag kullanmıyorsunuz. İlgili hashtagler ekleyerek erişiminizi artırabilirsiniz."
        )
    
    return {
        "current_metrics": {
            "avg_engagement_rate": round(avg_engagement, 2),
            "total_videos": len(videos),
            "total_views": sum(v.view_count for v in videos),
            "avg_views_per_video": round(sum(v.view_count for v in videos) / len(videos), 0)
        },
        "recommendations": recommendations
    }