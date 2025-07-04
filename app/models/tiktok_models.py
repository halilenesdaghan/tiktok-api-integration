# app/models/tiktok_models.py
from sqlalchemy import (Column, Integer, String, DateTime, Boolean, Text, ForeignKey, BigInteger, Float)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base

class TikTokUser(Base):
    __tablename__ = "tiktok_user"
    id = Column(Integer, primary_key=True, index=True)
    tiktok_open_id = Column(String(255), unique=True, nullable=False, index=True)
    tiktok_union_id = Column(String(255), unique=True, nullable=True)
    username = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    tokens = relationship("TikTokToken", back_populates="user", cascade="all, delete-orphan")
    ad_metrics = relationship("AdMetricsSnapshot", back_populates="user", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="user", cascade="all, delete-orphan")

class TikTokToken(Base):
    __tablename__ = "tiktok_token"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("tiktok_user.id"), nullable=False)
    access_token = Column(Text, nullable=False)  # Encrypted
    refresh_token = Column(Text, nullable=False) # Encrypted
    scope = Column(Text, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    refresh_expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user = relationship("TikTokUser", back_populates="tokens")

class AdMetricsSnapshot(Base):
    __tablename__ = "ad_metrics_snapshot"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("tiktok_user.id"), nullable=False)
    snapshot_ts = Column(DateTime(timezone=True), server_default=func.now())
    follower_count = Column(BigInteger)
    likes_count = Column(BigInteger)
    # ... Diğer metrikler ...
    profile_visits = Column(BigInteger)
    avg_watch_time_seconds = Column(Float)
    user = relationship("TikTokUser", back_populates="ad_metrics")

class Video(Base):
    __tablename__ = "video"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("tiktok_user.id"), nullable=False)
    video_id = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    publish_ts = Column(DateTime(timezone=True), nullable=False)
    user = relationship("TikTokUser", back_populates="videos")
    metrics = relationship("VideoMetricsSnapshot", back_populates="video", cascade="all, delete-orphan")

class VideoMetricsSnapshot(Base):
    __tablename__ = "video_metrics_snapshot"
    id = Column(Integer, primary_key=True)
    video_id = Column(Integer, ForeignKey("video.id"), nullable=False)
    snapshot_ts = Column(DateTime(timezone=True), server_default=func.now())
    views_total = Column(BigInteger)
    views_2s = Column(BigInteger)
    views_6s = Column(BigInteger)
    retention_pct_25 = Column(Float)
    retention_pct_100 = Column(Float)
    avg_play_time_seconds = Column(Float)
    video = relationship("Video", back_populates="metrics")