# app/core/security.py

from datetime import datetime, timedelta, timezone
from typing import Optional
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.config.settings import settings # settings'i import et

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
    # ... bu fonksiyon aynı kalabilir ...
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


# 3. Token Şifreleme Sınıfı
class TokenEncryption:
    """
    Hassas token'ları veritabanına kaydetmeden önce şifreler.
    """
    def __init__(self, key: str | bytes = None):
        # Eğer key dışarıdan verilmezse, her zaman settings'den al.
        if key is None:
            key = settings.TOKEN_ENCRYPTION_KEY

        if isinstance(key, str):
            key_bytes = key.encode('ascii')
        elif isinstance(key, bytes):
            key_bytes = key
        else:
            raise TypeError("Anahtar 'str' veya 'bytes' tipinde olmalıdır.")

        self.fernet = Fernet(key_bytes)

    def encrypt(self, data: str) -> str:
        # ... bu metod aynı kalabilir ...
        if not data:
            return ""
        encrypted_bytes = self.fernet.encrypt(data.encode('utf-8'))
        return encrypted_bytes.decode('ascii')

    def decrypt(self, encrypted_data: str) -> str:
        # ... bu metod aynı kalabilir ...
        if not encrypted_data:
            return ""
        encrypted_bytes = encrypted_data.encode('ascii')
        decrypted_bytes = self.fernet.decrypt(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')