# app/models/analytics.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, JSON, BigInteger
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class Analytics(Base):
    """
    Analytics modeli - Video ve hesap analitiği
    """
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Analitik türü: 'account', 'video', 'daily_summary'
    analytics_type = Column(String(50), nullable=False, index=True)
    
    # Video bilgileri (video analitiği için)
    video_id = Column(String(255), nullable=True, index=True)
    video_description = Column(String(500), nullable=True)
    
    # Metrikler
    view_count = Column(BigInteger, default=0)
    like_count = Column(BigInteger, default=0)
    comment_count = Column(BigInteger, default=0)
    share_count = Column(BigInteger, default=0)
    
    # Hesaplanan metrikler
    engagement_rate = Column(Float, default=0.0)
    
    # Zaman bilgisi
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    
    # Ek veriler (JSON)
    extra_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # İlişkiler
    user = relationship("User", back_populates="analytics")
    
    def __repr__(self):
        return f"<Analytics(id={self.id}, user_id={self.user_id}, type={self.analytics_type})>"


class VideoAnalytics(Base):
    """
    Video Analytics modeli - Detaylı video metrikleri
    """
    __tablename__ = "video_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Video bilgileri
    video_id = Column(String(255), nullable=False, index=True)
    video_description = Column(String(500), nullable=True)
    duration = Column(Integer, nullable=True)  # saniye cinsinden
    
    # Temel metrikler
    view_count = Column(BigInteger, default=0)
    like_count = Column(BigInteger, default=0)
    comment_count = Column(BigInteger, default=0)
    share_count = Column(BigInteger, default=0)
    
    # Video metadata
    cover_image_url = Column(String(500), nullable=True)
    share_url = Column(String(500), nullable=True)
    
    # Boyutlar
    height = Column(Integer, nullable=True)
    width = Column(Integer, nullable=True)
    
    # Zaman bilgileri
    video_created_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Hashtags (JSON array)
    hashtags = Column(JSON, nullable=True)

    # --- EKSİK OLAN VE YENİ EKLENEN BÖLÜM ---
    insights = relationship(
        "VideoInsights", 
        back_populates="video_analytics", 
        uselist=False, # Bir VideoAnalytics kaydının sadece bir VideoInsights kaydı olur (bire-bir ilişki)
        cascade="all, delete-orphan" # VideoAnalytics silinirse, bağlı VideoInsights da silinir
    )
    # -----------------------------------------
    
    def __repr__(self):
        return f"<VideoAnalytics(id={self.id}, video_id={self.video_id}, views={self.view_count})>"
    
class VideoInsights(Base):
    """
    Video Insights modeli - Commercial API metrikleri
    """
    __tablename__ = "video_insights"
    
    id = Column(Integer, primary_key=True, index=True)
    video_analytics_id = Column(Integer, ForeignKey("video_analytics.id"), nullable=False)
    
    # İzlenme metrikleri
    view_count_2s = Column(BigInteger, default=0)  # 2 saniye izlenme
    view_count_6s = Column(BigInteger, default=0)  # 6 saniye izlenme
    view_count_15s = Column(BigInteger, default=0) # 15 saniye izlenme
    
    # Retention oranları (yüzde)
    retention_rate_25 = Column(Float, default=0.0)   # %25 izlenme
    retention_rate_50 = Column(Float, default=0.0)   # %50 izlenme
    retention_rate_75 = Column(Float, default=0.0)   # %75 izlenme
    retention_rate_100 = Column(Float, default=0.0)  # %100 izlenme
    
    # Ortalama metrikler
    avg_watch_time = Column(Float, default=0.0)      # Ortalama izlenme süresi (saniye)
    avg_watch_time_per_user = Column(Float, default=0.0)  # Kullanıcı başına ortalama
    
    # Etkileşim detayları
    profile_visits = Column(BigInteger, default=0)   # Profil ziyaretleri
    follow_count = Column(BigInteger, default=0)     # Takip sayısı
    music_clicks = Column(BigInteger, default=0)     # Müzik tıklamaları
    
    # Anlık deneyim (instant experience) metrikleri
    instant_exp_view_time = Column(Float, default=0.0)  # Anlık deneyim izlenme süresi
    instant_exp_view_rate = Column(Float, default=0.0)  # Anlık deneyim izlenme oranı
    
    # Demografi (JSON)
    demographics = Column(JSON, nullable=True)  # Yaş, cinsiyet, konum dağılımı
    
    # Zaman bilgileri
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # İlişkiler
    video_analytics = relationship("VideoAnalytics", back_populates="insights")