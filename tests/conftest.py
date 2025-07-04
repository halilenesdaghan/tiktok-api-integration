# tests/conftest.py
import os
import sys
import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.config.database import Base, get_db
from app.config.settings import Settings


# Test settings override
class TestSettings(Settings):
    # Override settings for testing
    DATABASE_URL: str = "sqlite:///:memory:"
    REDIS_URL: str = "redis://localhost:6379/1"  # Use different DB for tests
    ENVIRONMENT: str = "testing"
    DEBUG: bool = True
    
    # Test TikTok credentials
    TIKTOK_CLIENT_KEY: str = "test_client_key"
    TIKTOK_CLIENT_SECRET: str = "test_client_secret"
    TIKTOK_REDIRECT_URI: str = "http://localhost:8000/auth/tiktok/callback"
    
    # Test security keys
    SECRET_KEY: str = "test-secret-key-for-testing-only-32-chars-long!"
    TOKEN_ENCRYPTION_KEY: str = "test-encryption-key-32-bytes-lng"
    TOKEN_ENCRYPTION_SALT: str = "test-salt-16byte"
    
    class Config:
        env_file = ".env.test"


# Override settings
test_settings = TestSettings()


# Test database setup
engine = create_engine(
    test_settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session")
def setup_database():
    """Setup test database"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(setup_database) -> Generator[Session, None, None]:
    """Get database session"""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db) -> Generator[TestClient, None, None]:
    """Get test client"""
    app.dependency_overrides[get_db] = lambda: db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Test user data"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def create_test_user(client, test_user_data):
    """Create test user and return user data with token"""
    # Register user
    response = client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 200
    user_data = response.json()
    
    # Login to get token
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user_data["username"],
            "password": test_user_data["password"]
        }
    )
    assert response.status_code == 200
    token_data = response.json()
    
    return {
        "user": user_data,
        "token": token_data["access_token"],
        "password": test_user_data["password"]
    }


@pytest.fixture
def auth_headers(create_test_user):
    """Get authentication headers"""
    return {"Authorization": f"Bearer {create_test_user['token']}"}


@pytest.fixture
def mock_tiktok_user_response():
    """Mock TikTok user API response"""
    return {
        "data": {
            "user": {
                "open_id": "test_open_id_123",
                "union_id": "test_union_id_123",
                "avatar_url": "https://example.com/avatar.jpg",
                "display_name": "Test TikTok User",
                "bio_description": "Test bio",
                "follower_count": 1000,
                "following_count": 500,
                "likes_count": 5000,
                "video_count": 50
            }
        }
    }


@pytest.fixture
def mock_tiktok_videos_response():
    """Mock TikTok videos API response"""
    return {
        "data": {
            "videos": [
                {
                    "id": "video_123",
                    "create_time": 1640995200,
                    "cover_image_url": "https://example.com/cover1.jpg",
                    "share_url": "https://tiktok.com/@test/video/123",
                    "video_description": "Test video 1",
                    "duration": 30,
                    "height": 1920,
                    "width": 1080,
                    "view_count": 10000,
                    "like_count": 1000,
                    "comment_count": 100,
                    "share_count": 50
                },
                {
                    "id": "video_456",
                    "create_time": 1641081600,
                    "cover_image_url": "https://example.com/cover2.jpg",
                    "share_url": "https://tiktok.com/@test/video/456",
                    "video_description": "Test video 2",
                    "duration": 45,
                    "height": 1920,
                    "width": 1080,
                    "view_count": 5000,
                    "like_count": 500,
                    "comment_count": 50,
                    "share_count": 25
                }
            ],
            "cursor": 12345,
            "has_more": True
        }
    }


@pytest.fixture
def mock_redis(monkeypatch):
    """Mock Redis client"""
    class MockRedis:
        def __init__(self):
            self.data = {}
        
        def get(self, key):
            return self.data.get(key)
        
        def set(self, key, value, ex=None):
            self.data[key] = value
            return True
        
        def setex(self, key, seconds, value):
            self.data[key] = value
            return True
        
        def delete(self, key):
            if key in self.data:
                del self.data[key]
                return 1
            return 0
        
        def keys(self, pattern):
            return [k for k in self.data.keys() if pattern.replace('*', '') in k]
        
        def ping(self):
            return True
        
        def pipeline(self):
            return self
        
        def zremrangebyscore(self, key, min_score, max_score):
            return 0
        
        def zcard(self, key):
            return 0
        
        def zadd(self, key, mapping):
            return 1
        
        def expire(self, key, seconds):
            return True
        
        def execute(self):
            return [0, 0, 1, True]
        
        def zrange(self, key, start, stop, withscores=False):
            return []
    
    mock_redis_instance = MockRedis()
    
    def mock_from_url(*args, **kwargs):
        return mock_redis_instance
    
    import redis
    monkeypatch.setattr(redis, "from_url", mock_from_url)
    
    return mock_redis_instance