import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from google.auth import exceptions as google_auth_exceptions
from src.config import settings
from src.db.base import get_db
from src.models.user import User
from src.api.deps import get_current_user, require_owner

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    name: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str
    shop_id: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class OkResponse(BaseModel):
    ok: bool = True


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if user is None or not pwd_ctx.verify(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({
        "sub": str(user.id),
        "shop_id": str(user.shop_id),
        "role": user.role,
        "email": user.email,
    })
    return TokenResponse(access_token=token)


@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        idinfo = id_token.verify_oauth2_token(
            request.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID or None,
        )
    except (ValueError, google_auth_exceptions.GoogleAuthError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    google_sub = idinfo.get("sub")
    if not google_sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")
    email = idinfo.get("email", "")
    if not idinfo.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google email not verified")

    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found. Request a demo to get access.",
            )
        user.google_id = google_sub
        await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "shop_id": str(user.shop_id),
        "role": user.role,
        "email": user.email,
    })
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfileResponse(id=str(user.id), email=user.email, name=user.name, role=user.role, shop_id=str(user.shop_id))


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: dict = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.name = body.name
    await db.commit()
    await db.refresh(user)
    return UserProfileResponse(id=str(user.id), email=user.email, name=user.name, role=user.role, shop_id=str(user.shop_id))


@router.patch("/password", response_model=OkResponse)
async def change_password(
    body: PasswordChange,
    current_user: dict = Depends(require_owner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if user is None or not pwd_ctx.verify(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.hashed_password = pwd_ctx.hash(body.new_password)
    await db.commit()
    return OkResponse()
