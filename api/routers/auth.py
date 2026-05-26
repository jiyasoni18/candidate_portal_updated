import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg
import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from jose import jwt

from api.dependencies import get_db
from config import settings
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _create_token(user_id: UUID) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


@router.post("/register", response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> TokenResponse:
    """Create a new user account and return a signed JWT."""
    hashed = _hash_password(body.password)
    try:
        row = await conn.fetchrow(
            """
            INSERT INTO users (full_name, email, hashed_password)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            body.full_name,
            body.email,
            hashed,
        )
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=409, detail="Email already registered.")
    except asyncpg.PostgresError as exc:
        logger.error("DB error during register: %s", exc)
        raise HTTPException(status_code=500, detail="Database error during registration.") from exc

    return TokenResponse(access_token=_create_token(row["id"]))


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db),
) -> TokenResponse:
    """Validate credentials and return a signed JWT."""
    try:
        row = await conn.fetchrow(
            "SELECT id, hashed_password FROM users WHERE email = $1",
            body.email,
        )
    except asyncpg.PostgresError as exc:
        logger.error("DB error during login: %s", exc)
        raise HTTPException(status_code=500, detail="Database error during login.") from exc

    if row is None or not _verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    return TokenResponse(access_token=_create_token(row["id"]))
