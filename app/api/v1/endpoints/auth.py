# app/api/v1/endpoints/auth.py

from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from typing import Optional
import logging
import json

from app.schemas.auth import UserCreate, User, Token, TikTokTokenResponse, OAuthCallback
from app.services.auth_service import auth_service
from app.core.security import create_access_token, verify_password, TokenEncryption
from app.config.database import get_db
from app.config.settings import settings
from app.core.oauth import tiktok_oauth_client
from app.core.cache import cache_manager
from app.models.user import User as UserModel
from app.models.token import Token as TokenModel

from fastapi.responses import JSONResponse

# --- YENİ EKLENDİ: Renkli Loglama için Yardımcı Sınıf ---
class ColorLogger:
    """Docker loglarında renkli çıktı üretmek için kullanılır."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

    @staticmethod
    def log(message):
        """Mesajı konsola yazdırır. Docker logları stdout'u yakalar."""
        print(message)

# ---------------------------------------------------------


router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Token encryption instance
token_encryption = TokenEncryption(settings.TOKEN_ENCRYPTION_KEY)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(UserModel).filter(UserModel.username == username))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    
    return user


@router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await auth_service.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    
    db_user = await auth_service.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken")
    
    return await auth_service.create_user(db=db, user=user)


@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authenticate": "Bearer"})
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer", "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60}


@router.get("/me", response_model=User)
async def get_current_user_info(current_user: UserModel = Depends(get_current_user)):
    return current_user


@router.post("/logout")
async def logout(current_user: UserModel = Depends(get_current_user)):
    return {"message": "Successfully logged out"}


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "healthy", "message": "Auth service is running."}


@router.get("/tiktok/authorize")
async def tiktok_authorize(current_user: UserModel = Depends(get_current_user)):
    try:
        auth_url, state, code_verifier = tiktok_oauth_client.get_authorization_url()
        cache_key = f"oauth_state:{state}"
        session_data = {"user_id": current_user.id, "code_verifier": code_verifier, "created_at": datetime.utcnow().isoformat()}
        await cache_manager.set(cache_key, session_data, expire=600)
        return {"authorization_url": auth_url, "state": state}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate authorization URL: {str(e)}")


@router.api_route("/tiktok/callback", methods=["GET", "POST"], status_code=status.HTTP_200_OK)
async def tiktok_callback_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
    callback_data: Optional[OAuthCallback] = None 
):
    """
    Handles both TikTok's URL verification and the OAuth code exchange.
    Logs incoming request parameters with colors for easy debugging in Docker.
    """
    # --- YENİ EKLENDİ: Gelen isteği renkli loglama ---
    log = ColorLogger.log
    c = ColorLogger
    
    log(f"\n{c.BOLD}{c.HEADER}--- TikTok Callback İsteği Alındı ---{c.ENDC}")
    log(f"{c.CYAN}Zaman:{c.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{c.CYAN}Metot:{c.ENDC} {c.YELLOW}{request.method}{c.ENDC}")
    
    # Query parametrelerini logla
    query_params = dict(request.query_params)
    log(f"{c.CYAN}Query Parametreleri:{c.ENDC}")
    if query_params:
        for key, value in query_params.items():
            log(f"  - {c.BLUE}{key}:{c.ENDC} {value}")
    else:
        log(f"  {c.YELLOW}(Query parametresi yok){c.ENDC}")

    # Body içeriğini logla (sadece POST için)
    log(f"{c.CYAN}Body İçeriği (callback_data):{c.ENDC}")
    if request.method == "POST":
        if callback_data:
            # Pydantic modelini dict'e çevirerek güzel bir formatta yazdır
            body_json = json.dumps(callback_data.dict(), indent=2)
            log(f"{c.GREEN}{body_json}{c.ENDC}")
        else:
             log(f"  {c.YELLOW}(Body içeriği boş veya parse edilemedi){c.ENDC}")
    else:
        log(f"  {c.YELLOW}(GET isteği olduğu için body yok){c.ENDC}")
    log(f"{c.BOLD}{c.HEADER}------------------------------------{c.ENDC}\n")
    # ----------------------------------------------------

    # 1. URL Doğrulama (Challenge Testi)
    challenge = request.query_params.get('challenge')
    if challenge:
        log(f"{c.GREEN}--> URL Doğrulama (Challenge) isteği algılandı. Challenge: {challenge}{c.ENDC}")
        return JSONResponse(content={'challenge': int(challenge)})

    # 2. Gerçek OAuth Akışı (Code Exchange)
    if request.method == "POST":
        log(f"{c.CYAN}--> OAuth Akışı (Code Exchange) başlatılıyor...{c.ENDC}")
        if not callback_data or not callback_data.code:
            error_message = "TikTok'tan gelen callback isteğinde 'code' veya 'state' parametreleri eksik."
            log(f"{c.RED}HATA: {error_message}{c.ENDC}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "CALLBACK_MISSING_PARAMS", "message": error_message})

        if callback_data.error:
            error_message = f"TikTok OAuth hatası: {callback_data.error_description or callback_data.error}"
            log(f"{c.RED}HATA: {error_message}{c.ENDC}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "TIKTOK_OAUTH_ERROR", "message": error_message})

        try:
            cache_key = f"oauth_state:{callback_data.state}"
            session_data = await cache_manager.get(cache_key)
            
            if not session_data:
                error_message = "Geçersiz veya süresi dolmuş OAuth state."
                log(f"{c.RED}HATA: {error_message}{c.ENDC}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "INVALID_OR_EXPIRED_STATE", "message": error_message})
            
            log(f"{c.GREEN}--> Geçerli OAuth state bulundu. Oturum verisi alınıyor...{c.ENDC}")
            user_id = session_data.get("user_id")
            code_verifier = session_data.get("code_verifier")
            
            if not user_id or not code_verifier:
                error_message = "Önbellekteki oturum verisinde 'user_id' veya 'code_verifier' bulunamadı."
                log(f"{c.RED}HATA: {error_message}{c.ENDC}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "INVALID_SESSION_DATA", "message": error_message})
            
            result = await db.execute(select(UserModel).filter(UserModel.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
            log(f"{c.CYAN}--> Code, access token ile değiştiriliyor...{c.ENDC}")
            token_data = await tiktok_oauth_client.get_access_token(code=callback_data.code, code_verifier=code_verifier)
            tiktok_token = TikTokTokenResponse(**token_data)
            log(f"{c.GREEN}--> Access token başarıyla alındı. Open ID: {tiktok_token.open_id}{c.ENDC}")
            
            result = await db.execute(select(TokenModel).filter(TokenModel.user_id == user.id, TokenModel.token_type == "tiktok"))
            existing_token = result.scalar_one_or_none()
            
            encrypted_access_token = token_encryption.encrypt(tiktok_token.access_token)
            encrypted_refresh_token = token_encryption.encrypt(tiktok_token.refresh_token)
            
            if existing_token:
                log(f"{c.CYAN}--> Mevcut token güncelleniyor...{c.ENDC}")
                existing_token.access_token = encrypted_access_token
                existing_token.refresh_token = encrypted_refresh_token
                existing_token.expires_at = datetime.utcnow() + timedelta(seconds=tiktok_token.expires_in)
                existing_token.open_id = tiktok_token.open_id
                existing_token.scopes = tiktok_token.scope
                existing_token.is_active = True
            else:
                log(f"{c.CYAN}--> Yeni token oluşturuluyor ve veritabanına ekleniyor...{c.ENDC}")
                new_token = TokenModel(user_id=user.id, token_type="tiktok", access_token=encrypted_access_token, refresh_token=encrypted_refresh_token, expires_at=datetime.utcnow() + timedelta(seconds=tiktok_token.expires_in), open_id=tiktok_token.open_id, scopes=tiktok_token.scope, is_active=True)
                db.add(new_token)
            
            user.tiktok_open_id = tiktok_token.open_id
            await db.commit()
            await cache_manager.delete(cache_key)
            
            log(f"{c.GREEN}{c.BOLD}--> TikTok hesabı başarıyla bağlandı! (UserID: {user.id}){c.ENDC}")
            return {"message": "TikTok account connected successfully", "open_id": tiktok_token.open_id, "user_id": user.id}
            
        except Exception as e:
            await db.rollback()
            log(f"{c.RED}{c.BOLD}--> BEKLENMEDİK HATA: {str(e)}{c.ENDC}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to connect TikTok account: {str(e)}")

    log(f"{c.YELLOW}--> Sadece GET isteği, işlem yapılmadı. Endpoint aktif.{c.ENDC}")
    return {"message": "TikTok callback endpoint is active."}