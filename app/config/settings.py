# app/config/settings.py

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    """
    Ana yapılandırma sınıfı. Tüm ayarlar .env dosyasından okunur veya burada varsayılan değerleri alır.
    """
    # PROJE AYARLARI (Uygulamanın ihtiyaç duyduğu varsayılanlar)
    PROJECT_NAME: str = "TikTok API Integration"
    PROJECT_DESCRIPTION: str = "Sosyal Medya Market Analizi Aracı – TikTok modülü"
    PROJECT_VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DOCS_URL: str = "/api/v1/docs"
    REDOC_URL: str = "/api/v1/redoc"
    
    # ORTAM AYARLARI (.env dosyasından okunacak)
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "info"

    # GÜVENLİK & JWT
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ALGORITHM: str = "HS256"

    # VERİTABANI & CACHE
    DATABASE_URL: str
    REDIS_URL: str

    # TIKTOK OAUTH BİLGİLERİ
    TIKTOK_CLIENT_KEY: str ="aw8k3l5unt6zdpz6"
    TIKTOK_CLIENT_SECRET: str ="ZQVJMrekFHwFEArLKVfZ8yeFCNwleNcB"
    TIKTOK_REDIRECT_URI: str = "https://ed60-193-140-111-38.ngrok-free.app/api/v1/auth/tiktok/callback"

    # TOKEN ŞİFRELEME
    TOKEN_ENCRYPTION_KEY: str = "wHhPZ1SPCxYEzOuWE8oJ-CD29UsbKIrujsaz5G65quQ="

    # CORS & RATE LIMIT
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:5500"
    RATE_LIMIT_PER_MINUTE: int = 60

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = True

settings = Settings()