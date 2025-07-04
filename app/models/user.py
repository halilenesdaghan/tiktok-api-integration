# app/models/user.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class User(Base):
    """
    Kullanıcı modeli - Sistem kullanıcıları
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # TikTok bağlantı bilgileri
    tiktok_open_id = Column(String(255), unique=True, nullable=True)
    tiktok_union_id = Column(String(255), nullable=True)
    tiktok_display_name = Column(String(255), nullable=True)
    tiktok_avatar_url = Column(Text, nullable=True)
    tiktok_follower_count = Column(Integer, default=0)
    tiktok_following_count = Column(Integer, default=0)
    tiktok_likes_count = Column(Integer, default=0)
    tiktok_video_count = Column(Integer, default=0)
    
    # İlişkiler
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"