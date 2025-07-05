# tests/test_auth.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config.database import Base, get_db
from app.models.user import User
from app.api.v1.endpoints.auth import get_password_hash


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client():
    """Test client fixture"""
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user():
    """Test user fixture"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "testpassword123",
        "full_name": "Test User"
    }


@pytest.fixture
def authenticated_client(client, test_user):
    """Authenticated test client fixture"""
    # Register user
    response = client.post(
        f"/api/v1/auth/register",
        json=test_user
    )
    assert response.status_code == 200
    
    # Login
    response = client.post(
        f"/api/v1/auth/login",
        data={
            "username": test_user["username"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    # Add auth header
    client.headers = {"Authorization": f"Bearer {token}"}
    return client

@pytest.mark.asyncio
async def test_tiktok_callback_get_request_success(self, authenticated_client, db, mock_redis):
    """Test the corrected GET-based OAuth callback flow."""
    # 1. Authorize endpoint'ini çağırarak state ve verifier'ı cache'e kaydet
    response = authenticated_client.get("/api/v1/auth/tiktok/authorize")
    assert response.status_code == 200
    auth_data = response.json()
    state = auth_data["state"]

    # 2. TikTok'un geri yönlendirmesini simüle et
    # Bu aşamada, get_access_token'i mock'lamak gerekir.
    with patch("app.core.oauth.TikTokOAuth2.get_access_token") as mock_get_token:
        mock_get_token.return_value = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "open_id": "mock_open_id",
            "scope": "user.info.basic",
            "expires_in": 7200,
            "refresh_expires_in": 86400,
            "token_type": "Bearer"
        }

        # Callback URL'e GET isteği yap
        callback_response = authenticated_client.get(
            f"/api/v1/auth/tiktok/callback?code=mock_auth_code&state={state}"
        )

        assert callback_response.status_code == 200
        assert "TikTok account connected successfully" in callback_response.json()["message"]

        # Veritabanında token'ın kaydedildiğini kontrol et
        token_in_db = db.query(TokenModel).filter(TokenModel.open_id == "mock_open_id").first()
        assert token_in_db is not None
        assert token_in_db.token_type == "tiktok"

class TestAuth:
    """Authentication tests"""
    
    def test_register_user(self, client, test_user):
        """Test user registration"""
        response = client.post(
            f"/api/v1/auth/register",
            json=test_user
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["username"] == test_user["username"]
        assert "id" in data
        assert "hashed_password" not in data
    
    def test_register_duplicate_email(self, client, test_user):
        """Test duplicate email registration"""
        # First registration
        client.post(f"/api/v1/auth/register", json=test_user)
        
        # Second registration with same email
        response = client.post(
            f"/api/v1/auth/register",
            json=test_user
        )
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]
    
    def test_register_duplicate_username(self, client, test_user):
        """Test duplicate username registration"""
        # First registration
        client.post(f"/api/v1/auth/register", json=test_user)
        
        # Second registration with different email but same username
        test_user["email"] = "another@example.com"
        response = client.post(
            f"/api/v1/auth/register",
            json=test_user
        )
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        # Register user first
        client.post(f"/api/v1/auth/register", json=test_user)
        
        # Login
        response = client.post(
            f"/api/v1/auth/login",
            data={
                "username": test_user["username"],
                "password": test_user["password"]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        # Register user first
        client.post(f"/api/v1/auth/register", json=test_user)
        
        # Login with wrong password
        response = client.post(
            f"/api/v1/auth/login",
            data={
                "username": test_user["username"],
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            f"/api/v1/auth/login",
            data={
                "username": "nonexistent",
                "password": "password"
            }
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_get_current_user(self, authenticated_client, test_user):
        """Test get current user info"""
        response = authenticated_client.get(f"/api/v1/auth/me")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user["email"]
        assert data["username"] == test_user["username"]
        assert "hashed_password" not in data
    
    def test_get_current_user_unauthorized(self, client):
        """Test get current user without auth"""
        response = client.get(f"/api/v1/auth/me")
        assert response.status_code == 401
    
    def test_logout(self, authenticated_client):
        """Test logout"""
        response = authenticated_client.post(f"/api/v1/auth/logout")
        assert response.status_code == 200
        assert "Successfully logged out" in response.json()["message"]
    
    def test_tiktok_authorize(self, authenticated_client):
        """Test TikTok authorization URL generation"""
        response = authenticated_client.get(
            f"/api/v1/auth/tiktok/authorize",
            params={"scopes": "user.info.basic,video.list"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "authorization_url" in data
        assert "tiktok.com" in data["authorization_url"]
        assert "client_key=" in data["authorization_url"]