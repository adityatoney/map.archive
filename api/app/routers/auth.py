"""Authentication router."""

from pydantic import BaseModel, EmailStr
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.models.user import User
from app.utils.auth import create_access_token, get_current_user, verify_password

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str | None


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT token."""
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token = create_access_token(data={"sub": user.email})
    return LoginResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(user=Depends(get_current_user)):
    """Refresh an existing JWT token (must still be valid)."""
    token = create_access_token(data={"sub": user.email})
    return LoginResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
    )
