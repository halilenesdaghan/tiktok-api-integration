# app/config/database.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from .settings import settings

# URL'i async uyumlu hale getir
def get_database_url():
    """Database URL'ini async uyumlu hale getirir"""
    db_url = settings.DATABASE_URL
    
    # PostgreSQL için asyncpg driver'ı kullan
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
    # SQLite için aiosqlite driver'ı kullan
    elif db_url.startswith("sqlite://"):
        db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")
    
    return db_url

# Asenkron engine oluştur
async_engine = create_async_engine(
    get_database_url(),
    echo=settings.DEBUG,  # DEBUG modda SQL sorgularını loglar
    pool_pre_ping=True,
    # SQLite için özel ayarlar
    connect_args={"check_same_thread": False} if "sqlite" in get_database_url() else {}
)

# Asenkron oturumlar için factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Tüm modellerimizin miras alacağı temel Base sınıfı
Base = declarative_base()

# Asenkron veritabanı oturumu için dependency
async def get_db() -> AsyncSession:
    """
    Dependency function that yields an async session.
    Bu yapı, her istek için bir oturum açar, işlem bitince kapatır.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Uygulama başlangıcında veritabanı tablolarını oluşturur.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)