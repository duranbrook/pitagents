import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from passlib.context import CryptContext
from src.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

# In-memory test users (production would use a real DB lookup)
_TEST_USERS: dict = {
    "owner@shop.com": {
        "id": "00000000-0000-0000-0000-000000000001",
        "role": "owner",
        "hashed_password": pwd_ctx.hash("testpass"),
    },
    "tech@shop.com": {
        "id": "00000000-0000-0000-0000-000000000002",
        "role": "technician",
        "hashed_password": pwd_ctx.hash("testpass"),
    },
}


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
async def login(request: LoginRequest) -> TokenResponse:
    user = _TEST_USERS.get(request.email)
    if user is None or not pwd_ctx.verify(request.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token({"sub": user["id"], "role": user["role"], "email": request.email})
    return TokenResponse(access_token=token)
