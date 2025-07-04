# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.config.settings import settings

# 1. Şifre Hash'leme için Passlib Context'i
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Düz metin şifreyi, hash'lenmiş versiyonu ile karşılaştırır."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Düz metin şifreyi hash'ler."""
    return pwd_context.hash(password)


# 2. JWT (JSON Web Token) İşlemleri
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Verilen data ve süreye göre bir JWT access token oluşturur."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Eğer süre belirtilmezse, varsayılan olarak 15 dakika ekle
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# 3. Token Şifreleme Sınıfı
class TokenEncryption:
    """
    Hassas token'ları (örn. TikTok access_token) veritabanına kaydetmeden önce
    şifrelemek ve okurken şifresini çözmek için kullanılır.
    """
    def __init__(self, key: str | bytes = None):
        """
        Bir Fernet anahtarı ile sınıfı başlatır.

        Args:
            key: Fernet anahtarı (str veya bytes). 
                 Eğer None ise, settings.TOKEN_ENCRYPTION_KEY kullanılır.
        """
        if key is None:
            # key = settings.TOKEN_ENCRYPTION_KEY
            # Örnek olarak anahtarı burada tanımlıyorum:
            key = "L8poBUJPRWeYJudhwR9k_j9u7xyEkOts0j1kskJdQaA="

        # Fernet anahtarı HER ZAMAN bytes olmalıdır.
        # Eğer string ise, kullanmadan önce bytes'a çeviririz.
        if isinstance(key, str):
            key_bytes = key.encode('ascii')
        elif isinstance(key, bytes):
            key_bytes = key
        else:
            raise TypeError("Anahtar 'str' veya 'bytes' tipinde olmalıdır.")

        self.fernet = Fernet(key_bytes)

    def encrypt(self, data: str) -> str:
        """Verilen string'i şifreler ve string olarak döndürür."""
        if not data:
            return ""
        # Şifrelenecek veri bytes olmalı
        encrypted_bytes = self.fernet.encrypt(data.encode('utf-8'))
        # Saklaması kolay olması için sonucu string'e çevir
        return encrypted_bytes.decode('ascii')

    def decrypt(self, encrypted_data: str) -> str:
        """Şifrelenmiş string'i çözer."""
        if not encrypted_data:
            return ""
        # Şifresi çözülecek veri bytes olmalı
        encrypted_bytes = encrypted_data.encode('ascii')
        # Sonuç bytes olarak döner
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        # Orijinal string'i elde etmek için decode et
        return decrypted_bytes.decode('utf-8')