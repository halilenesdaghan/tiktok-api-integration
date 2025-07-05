# app/api/v1/endpoints/auth.py

from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import RedirectResponse
from fastapi import Depends
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError, jwt
from typing import Optional
from urllib.parse import urlencode
import logging
import json
import secrets

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

@router.get("/login/tiktok")
async def login_tiktok():
    state = secrets.token_urlsafe(16)
    
    # Kapsamları (scopes) ihtiyacınıza göre düzenleyin
    scopes = "user.info.basic,video.list,artist.certification.read,artist.certification.update,user.info.profile,user.info.stats,video.list" 

    # Parametreleri oluştur
    params = {
        'client_key': settings.TIKTOK_CLIENT_KEY,
        'scope': scopes,
        'response_type': 'code',
        'redirect_uri': settings.TIKTOK_REDIRECT_URI,
        'state': state,
        # Dokümanlarda isteniyorsa diğer PKCE parametreleri (code_challenge, code_challenge_method) eklenebilir.
    }
    
    # TikTok yetkilendirme URL'ini oluştur
    tiktok_auth_url = f"https://www.tiktok.com/v2/auth/authorize/?{urlencode(params)}"
    
    # Kullanıcıyı bu URL'e yönlendir
    return RedirectResponse(url=tiktok_auth_url)

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


@router.api_route("/tiktok/callback", methods=["GET", "POST"], summary="Handles TikTok OAuth callback and webhooks")
async def tiktok_callback_handler(
    request: Request,
    db: AsyncSession = Depends(get_db),
    # GET isteği için query parametrelerini doğrudan al
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    challenge: Optional[int] = Query(None) # Webhook için challenge
):
    """
    Handles both TikTok's URL verification (via GET with challenge) and the OAuth code exchange (via GET with code and state).
    Logs incoming request parameters for easy debugging.
    """
    log = ColorLogger.log
    c = ColorLogger

    log(f"\n{c.BOLD}{c.HEADER}--- TikTok Callback/Webhook Request Received ---{c.ENDC}")
    log(f"{c.CYAN}Timestamp:{c.ENDC} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"{c.CYAN}Method:{c.ENDC} {c.YELLOW}{request.method}{c.ENDC}")
    log(f"{c.CYAN}Query Params:{c.ENDC} {dict(request.query_params)}")

    # 1. Webhook URL Doğrulama (Challenge Testi)
    if request.method == "GET" and challenge is not None:
        log(f"{c.GREEN}--> URL Verification (Challenge) detected. Challenge: {challenge}{c.ENDC}")
        return JSONResponse(content={'challenge': challenge})

    # 2. OAuth Akışı (Code Exchange) - Artık GET ile çalışıyor
    if request.method == "GET" and code and state:
        log(f"{c.CYAN}--> OAuth Flow (Code Exchange) initiated...{c.ENDC}")

        if error:
            error_message = f"TikTok OAuth error: {error_description or error}"
            log(f"{c.RED}ERROR: {error_message}{c.ENDC}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "TIKTOK_OAUTH_ERROR", "message": error_message})

        try:
            cache_key = f"oauth_state:{state}"
            session_data = await cache_manager.get(cache_key)
            
            if not session_data:
                error_message = "Invalid or expired OAuth state. Please try logging in again."
                log(f"{c.RED}ERROR: {error_message}{c.ENDC}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "INVALID_OR_EXPIRED_STATE", "message": error_message})
            
            log(f"{c.GREEN}--> Valid OAuth state found. Retrieving session data...{c.ENDC}")
            user_id = session_data.get("user_id")
            code_verifier = session_data.get("code_verifier")
            
            if not user_id or not code_verifier:
                error_message = "Could not find 'user_id' or 'code_verifier' in cached session data."
                log(f"{c.RED}ERROR: {error_message}{c.ENDC}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error_code": "INVALID_SESSION_DATA", "message": error_message})
            
            user = await db.get(UserModel, user_id)
            if not user:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
            
            log(f"{c.CYAN}--> Exchanging authorization code for an access token...{c.ENDC}")
            token_data = await tiktok_oauth_client.get_access_token(code=code, code_verifier=code_verifier)
            tiktok_token = TikTokTokenResponse(**token_data)
            log(f"{c.GREEN}--> Access token successfully obtained. Open ID: {tiktok_token.open_id}{c.ENDC}")
            
            # Var olan token'ı bul veya yeni oluştur
            result = await db.execute(select(TokenModel).filter(TokenModel.user_id == user.id, TokenModel.token_type == "tiktok"))
            existing_token = result.scalar_one_or_none()
            
            encrypted_access_token = token_encryption.encrypt(tiktok_token.access_token)
            encrypted_refresh_token = token_encryption.encrypt(tiktok_token.refresh_token)
            
            if existing_token:
                log(f"{c.CYAN}--> Updating existing token...{c.ENDC}")
                existing_token.access_token = encrypted_access_token
                existing_token.refresh_token = encrypted_refresh_token
                existing_token.expires_at = datetime.utcnow() + timedelta(seconds=tiktok_token.expires_in)
                existing_token.open_id = tiktok_token.open_id
                existing_token.scopes = tiktok_token.scope
                existing_token.is_active = True
            else:
                log(f"{c.CYAN}--> Creating and storing a new token...{c.ENDC}")
                new_token = TokenModel(
                    user_id=user.id, token_type="tiktok", 
                    access_token=encrypted_access_token, 
                    refresh_token=encrypted_refresh_token, 
                    expires_at=datetime.utcnow() + timedelta(seconds=tiktok_token.expires_in), 
                    open_id=tiktok_token.open_id, 
                    scopes=tiktok_token.scope, 
                    is_active=True
                )
                db.add(new_token)
            
            user.tiktok_open_id = tiktok_token.open_id
            await db.commit()
            await cache_manager.delete(cache_key)
            
            log(f"{c.GREEN}{c.BOLD}--> TikTok account connected successfully! (UserID: {user.id}){c.ENDC}")
            # Kullanıcıyı başarılı bir sayfaya yönlendir
            return {"message": "TikTok account connected successfully. You can close this tab."}
            
        except Exception as e:
            await db.rollback()
            log(f"{c.RED}{c.BOLD}--> UNEXPECTED ERROR: {str(e)}{c.ENDC}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to connect TikTok account: {str(e)}")

    # Diğer tüm durumlar için varsayılan yanıt
    log(f"{c.YELLOW}--> Unhandled GET/POST request. Endpoint is active.{c.ENDC}")
    return {"message": "TikTok callback endpoint is active and waiting for a valid request."}