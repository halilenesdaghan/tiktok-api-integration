# app/services/auth_service.py

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.user import User
from app.schemas.auth import UserCreate
from app.core.security import get_password_hash, verify_password


class AuthService:
    """Authentication service"""
    
    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email"""
        result = await db.execute(
            select(User).filter(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Get user by username"""
        result = await db.execute(
            select(User).filter(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, db: AsyncSession, user: UserCreate) -> User:
        """Create new user"""
        hashed_password = get_password_hash(user.password)
        
        db_user = User(
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password
        )
        
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        
        return db_user
    
    async def authenticate_user(
        self, 
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """Authenticate user with username and password"""
        user = await self.get_user_by_username(db, username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user


# Create service instance
auth_service = AuthService()