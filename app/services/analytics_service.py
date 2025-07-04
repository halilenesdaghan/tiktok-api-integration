# app/services/analytics_service.py

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class AnalyticsService:
    """Analytics service for processing TikTok data"""
    
    def calculate_engagement_metrics(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate engagement metrics from video data"""
        if not videos:
            return {
                "total_videos": 0,
                "total_views": 0,
                "total_likes": 0,
                "total_comments": 0,
                "total_shares": 0,
                "avg_engagement_rate": 0.0,
                "avg_views_per_video": 0.0,
                "most_viewed_video": None,
                "best_engagement_video": None
            }
        
        total_views = sum(v.get("view_count", 0) for v in videos)
        total_likes = sum(v.get("like_count", 0) for v in videos)
        total_comments = sum(v.get("comment_count", 0) for v in videos)
        total_shares = sum(v.get("share_count", 0) for v in videos)
        
        # Calculate engagement rates
        engagement_rates = []
        for video in videos:
            views = video.get("view_count", 0)
            if views > 0:
                engagement = (
                    video.get("like_count", 0) + 
                    video.get("comment_count", 0) + 
                    video.get("share_count", 0)
                ) / views * 100
                engagement_rates.append(engagement)
                video["engagement_rate"] = engagement
            else:
                video["engagement_rate"] = 0
        
        avg_engagement_rate = sum(engagement_rates) / len(engagement_rates) if engagement_rates else 0
        
        # Find best videos
        most_viewed = max(videos, key=lambda x: x.get("view_count", 0)) if videos else None
        best_engagement = max(videos, key=lambda x: x.get("engagement_rate", 0)) if videos else None
        
        return {
            "total_videos": len(videos),
            "total_views": total_views,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "total_shares": total_shares,
            "avg_engagement_rate": round(avg_engagement_rate, 2),
            "avg_views_per_video": round(total_views / len(videos), 0) if videos else 0,
            "most_viewed_video": {
                "id": most_viewed.get("id"),
                "view_count": most_viewed.get("view_count", 0),
                "description": most_viewed.get("video_description", "")[:100]
            } if most_viewed else None,
            "best_engagement_video": {
                "id": best_engagement.get("id"),
                "engagement_rate": round(best_engagement.get("engagement_rate", 0), 2),
                "description": best_engagement.get("video_description", "")[:100]
            } if best_engagement else None
        }
    
    def calculate_growth_trends(self, videos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate growth trends from video data"""
        if not videos or len(videos) < 2:
            return {
                "weekly_view_trend": 0.0,
                "weekly_engagement_trend": 0.0,
                "posting_frequency": 0.0,
                "best_performing_week": None
            }
        
        # Sort videos by create time
        sorted_videos = sorted(videos, key=lambda x: x.get("create_time", 0))
        
        # Group by weeks
        weekly_data = defaultdict(lambda: {
            "views": 0,
            "engagement": 0,
            "count": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0
        })
        
        for video in sorted_videos:
            create_time = video.get("create_time", 0)
            if create_time:
                week_date = datetime.fromtimestamp(create_time)
                week_key = week_date.strftime("%Y-W%U")
                
                weekly_data[week_key]["views"] += video.get("view_count", 0)
                weekly_data[week_key]["likes"] += video.get("like_count", 0)
                weekly_data[week_key]["comments"] += video.get("comment_count", 0)
                weekly_data[week_key]["shares"] += video.get("share_count", 0)
                weekly_data[week_key]["count"] += 1
                
                # Calculate engagement
                views = video.get("view_count", 0)
                if views > 0:
                    engagement = (
                        video.get("like_count", 0) + 
                        video.get("comment_count", 0) + 
                        video.get("share_count", 0)
                    ) / views * 100
                    weekly_data[week_key]["engagement"] += engagement
        
        # Get recent weeks
        sorted_weeks = sorted(weekly_data.keys())
        recent_weeks = sorted_weeks[-4:] if len(sorted_weeks) >= 4 else sorted_weeks
        
        # Calculate trends
        if len(recent_weeks) >= 2:
            # View trend
            recent_views = [weekly_data[week]["views"] for week in recent_weeks]
            view_trend = self._calculate_trend(recent_views)
            
            # Engagement trend
            recent_engagement = [
                weekly_data[week]["engagement"] / weekly_data[week]["count"] 
                if weekly_data[week]["count"] > 0 else 0 
                for week in recent_weeks
            ]
            engagement_trend = self._calculate_trend(recent_engagement)
        else:
            view_trend = 0.0
            engagement_trend = 0.0
        
        # Calculate posting frequency (videos per week)
        total_weeks = len(weekly_data)
        total_videos = len(videos)
        posting_frequency = total_videos / total_weeks if total_weeks > 0 else 0
        
        # Find best performing week
        best_week = max(
            weekly_data.items(),
            key=lambda x: x[1]["views"]
        ) if weekly_data else None
        
        return {
            "weekly_view_trend": round(view_trend, 2),
            "weekly_engagement_trend": round(engagement_trend, 2),
            "posting_frequency": round(posting_frequency, 2),
            "best_performing_week": best_week[0] if best_week else None
        }
    
    def _calculate_trend(self, values: List[float]) -> float:
        """Calculate trend percentage from a list of values"""
        if len(values) < 2:
            return 0.0
        
        # Remove zero values from the beginning
        non_zero_values = []
        for v in values:
            if v > 0 or non_zero_values:
                non_zero_values.append(v)
        
        if len(non_zero_values) < 2:
            return 0.0
        
        # Calculate average of first half vs second half
        mid = len(non_zero_values) // 2
        first_half_avg = sum(non_zero_values[:mid]) / mid if mid > 0 else 0
        second_half_avg = sum(non_zero_values[mid:]) / len(non_zero_values[mid:]) if non_zero_values[mid:] else 0
        
        if first_half_avg == 0:
            return 100.0 if second_half_avg > 0 else 0.0
        
        trend = ((second_half_avg - first_half_avg) / first_half_avg) * 100
        return trend