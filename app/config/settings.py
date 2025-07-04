# app/config/settings.py

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """
    Ana yapılandırma sınıfı. Tüm ayarlar .env dosyasından okunur.
    """
    # PROJE AYARLARI
    PROJECT_NAME: str = "TikTok API Integration"
    PROJECT_DESCRIPTION: str = "Sosyal Medya Market Analizi Aracı – TikTok modülü"
    PROJECT_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"

    # GÜVENLİK & JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # VERİTABANI
    DATABASE_URL: str

    # REDIS (Cache & Rate Limiting)
    REDIS_URL: str

    # TIKTOK OAUTH BİLGİLERİ
    TIKTOK_CLIENT_KEY: str
    TIKTOK_CLIENT_SECRET: str
    TIKTOK_REDIRECT_URI: str

    # TOKEN ŞİFRELEME (Fernet)
    FERNET_KEY: str ="L8poBUJPRWeYJudhwR9k_j9u7xyEkOts0j1kskJdQaA="
    TOKEN_ENCRYPTION_KEY: str = "L8poBUJPRWeYJudhwR9k_j9u7xyEkOts0j1kskJdQaA="

    # API & CORS
    API_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/api/v1/docs"
    REDOC_URL: str = "/api/v1/redoc"
    
    # Frontend uygulamanızın adresleri (virgülle ayırın)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:5500"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

# Ayarları kullanmak için bir nesne oluştur
settings = Settings()