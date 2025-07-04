# tests/test_tiktok.py
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timedelta
import json

from app.models.token import Token
from app.models.user import User
from app.core.security import TokenEncryption


class TestTikTokAPI:
    """TikTok API endpoint tests"""
    
    @pytest.fixture
    def setup_tiktok_token(self, db, create_test_user):
        """Setup TikTok token for user"""
        user_data = create_test_user
        user = db.query(User).filter(User.username == "testuser").first()
        
        # Create encrypted token
        token_encryption = TokenEncryption()
        encrypted_access_token = token_encryption.encrypt_token("test_tiktok_access_token")
        encrypted_refresh_token = token_encryption.encrypt_token("test_tiktok_refresh_token")
        
        # Create token in database
        token = Token(
            user_id=user.id,
            token_type="tiktok",
            access_token=encrypted_access_token,
            refresh_token=encrypted_refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=1),
            open_id="test_open_id_123",
            scopes="user.info.basic,video.list",
            is_active=True
        )
        db.add(token)
        db.commit()
        
        return user_data
    
    @patch('app.services.tiktok_service.httpx.AsyncClient')
    async def test_get_user_info(
        self, 
        mock_httpx, 
        client, 
        auth_headers, 
        setup_tiktok_token,
        mock_tiktok_user_response
    ):
        """Test get TikTok user info"""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_tiktok_user_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.return_value = mock_client
        
        # Make request
        response = client.get(
            "/api/v1/tiktok/user/info",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["open_id"] == "test_open_id_123"
        assert data["display_name"] == "Test TikTok User"
        assert data["follower_count"] == 1000
    
    def test_get_user_info_no_token(self, client, auth_headers):
        """Test get user info without TikTok token"""
        response = client.get(
            "/api/v1/tiktok/user/info",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "TikTok account not connected" in response.json()["detail"]
    
    def test_get_user_info_expired_token(self, db, client, auth_headers, create_test_user):
        """Test get user info with expired token"""
        user = db.query(User).filter(User.username == "testuser").first()
        
        # Create expired token
        token_encryption = TokenEncryption()
        token = Token(
            user_id=user.id,
            token_type="tiktok",
            access_token=token_encryption.encrypt_token("expired_token"),
            refresh_token=token_encryption.encrypt_token("expired_refresh"),
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired
            is_active=True
        )
        db.add(token)
        db.commit()
        
        response = client.get(
            "/api/v1/tiktok/user/info",
            headers=auth_headers
        )
        
        assert response.status_code == 401
        assert "TikTok token expired" in response.json()["detail"]
    
    @patch('app.services.tiktok_service.httpx.AsyncClient')
    async def test_get_user_videos(
        self,
        mock_httpx,
        client,
        auth_headers,
        setup_tiktok_token,
        mock_tiktok_videos_response
    ):
        """Test get user videos"""
        # Mock httpx response
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_tiktok_videos_response
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value.get.return_value = mock_response
        mock_httpx.return_value = mock_client
        
        # Make request
        response = client.get(
            "/api/v1/tiktok/videos",
            headers=auth_headers,
            params={"max_count": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == 2
        assert data["videos"][0]["id"] == "video_123"
        assert data["has_more"] is True
        assert data["cursor"] == 12345
    
    @patch('app.services.tiktok_service.httpx.AsyncClient')
    async def test_sync_tiktok_data(
        self,
        mock_httpx,
        client,
        db,
        auth_headers,
        setup_tiktok_token,
        mock_tiktok_user_response,
        mock_tiktok_videos_response
    ):
        """Test sync TikTok data"""
        # Setup mock responses
        mock_user_response = AsyncMock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = mock_tiktok_user_response
        
        mock_videos_response = AsyncMock()
        mock_videos_response.status_code = 200
        mock_videos_response.json.return_value = mock_tiktok_videos_response
        
        # Mock client with different responses
        mock_client = AsyncMock()
        mock_get = mock_client.__aenter__.return_value.get
        
        # First call returns user info, subsequent calls return videos
        mock_get.side_effect = [mock_user_response, mock_videos_response]
        mock_httpx.return_value = mock_client
        
        # Make sync request
        response = client.post(
            "/api/v1/tiktok/sync",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_synced"] is True
        assert data["videos_synced"] > 0
        assert "Sync completed successfully" in data["message"]
        
        # Check if data was saved to database
        from app.models.analytics import VideoAnalytics
        videos = db.query(VideoAnalytics).all()
        assert len(videos) == 2
    
    def test_get_video_analytics(self, db, client, auth_headers, create_test_user):
        """Test get video analytics"""
        user = db.query(User).filter(User.username == "testuser").first()
        
        # Create video analytics data
        from app.models.analytics import VideoAnalytics
        video = VideoAnalytics(
            user_id=user.id,
            video_id="test_video_123",
            video_description="Test video",
            view_count=1000,
            like_count=100,
            comment_count=10,
            share_count=5
        )
        db.add(video)
        db.commit()
        
        response = client.get(
            f"/api/v1/tiktok/videos/test_video_123",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == "test_video_123"
        assert data["view_count"] == 1000
        assert "engagement_rate" in data
        assert data["engagement_rate"] == 11.5  # (100+10+5)/1000*100
    
    def test_get_video_analytics_not_found(self, client, auth_headers):
        """Test get non-existent video analytics"""
        response = client.get(
            "/api/v1/tiktok/videos/nonexistent_video",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "Video analytics not found" in response.json()["detail"]
    
    @patch('app.services.tiktok_service.httpx.AsyncClient')
    async def test_get_analytics_summary(
        self,
        mock_httpx,
        db,
        client,
        auth_headers,
        create_test_user
    ):
        """Test get analytics summary"""
        user = db.query(User).filter(User.username == "testuser").first()
        
        # Update user TikTok info
        user.tiktok_open_id = "test_open_id"
        user.tiktok_display_name = "Test User"
        user.tiktok_follower_count = 1000
        user.tiktok_video_count = 10
        
        # Create some video analytics data
        from app.models.analytics import VideoAnalytics
        for i in range(3):
            video = VideoAnalytics(
                user_id=user.id,
                video_id=f"video_{i}",
                video_description=f"Test video {i}",
                view_count=1000 * (i + 1),
                like_count=100 * (i + 1),
                comment_count=10 * (i + 1),
                share_count=5 * (i + 1),
                video_created_at=datetime.utcnow() - timedelta(days=i)
            )
            db.add(video)
        db.commit()
        
        response = client.get(
            "/api/v1/tiktok/analytics/summary",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check user info
        assert data["user_info"]["display_name"] == "Test User"
        assert data["user_info"]["follower_count"] == 1000
        
        # Check engagement metrics
        assert data["engagement_metrics"]["total_videos"] == 3
        assert data["engagement_metrics"]["total_views"] == 6000  # 1000 + 2000 + 3000
        assert data["engagement_metrics"]["total_likes"] == 600   # 100 + 200 + 300
        
        # Check if recent videos are included
        assert len(data["recent_videos"]) == 3