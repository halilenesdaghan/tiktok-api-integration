# app/models/token.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.config.database import Base


class Token(Base):
    """
    Token modeli - OAuth ve API tokenları
    """
    __tablename__ = "tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Token türü: 'tiktok', 'system', 'refresh'
    token_type = Column(String(50), nullable=False)
    
    # Şifrelenmiş tokenlar
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    
    # Token metadata
    expires_at = Column(DateTime(timezone=True), nullable=True)
    scopes = Column(Text, nullable=True)  # JSON string olarak saklanır
    
    # TikTok specific
    open_id = Column(String(255), nullable=True)
    
    # Token durumu
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # İlişkiler
    user = relationship("User", back_populates="tokens")
    
    def __repr__(self):
        return f"<Token(id={self.id}, user_id={self.user_id}, type={self.token_type})>"