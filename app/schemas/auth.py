# app/schemas/auth.py
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List # Optional'ı import ettiğinizden emin olun
from pydantic import BaseModel, EmailStr, Field

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8)


class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    tiktok_open_id: Optional[str] = None
    tiktok_display_name: Optional[str] = None
    tiktok_follower_count: Optional[int] = None
    
    class Config:
        from_attributes = True


class User(UserInDB):
    pass


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: Optional[int] = None


class TokenData(BaseModel):
    user_id: Optional[int] = None
    username: Optional[str] = None
    scopes: List[str] = []


# OAuth Schemas
class OAuthAuthorize(BaseModel):
    scopes: str = "user.info.basic"
    state: Optional[str] = None


class OAuthCallback(BaseModel):
    # 'code' alanını isteğe bağlı hale getiriyoruz
    code: Optional[str] = None 
    state: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


class TikTokTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    open_id: str
    scope: str
    expires_in: int
    refresh_expires_in: int
    token_type: str = "Bearer"


# Login/Register Schemas
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(UserCreate):
    pass


class PasswordReset(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8)