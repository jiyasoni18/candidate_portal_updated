"""Unit tests for the get_current_user_id dependency.

Requirements: 3.5, 4.2
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwt

from api.dependencies import get_current_user_id
from config import settings


def _make_token(user_id: UUID, expire_delta: timedelta = timedelta(hours=1)) -> str:
    expire = datetime.now(timezone.utc) + expire_delta
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# Valid token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_valid_token_returns_correct_uuid():
    """Requirement 3.5: valid JWT returns the correct user UUID."""
    user_id = uuid4()
    token = _make_token(user_id)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    result = await get_current_user_id(credentials=creds)

    assert result == user_id


# ---------------------------------------------------------------------------
# Missing token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_token_raises_401():
    """Requirement 4.2: missing Authorization header raises HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(credentials=None)

    assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Expired token
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_expired_token_raises_401():
    """Requirement 3.5 / 4.2: expired JWT raises HTTP 401."""
    user_id = uuid4()
    token = _make_token(user_id, expire_delta=timedelta(seconds=-1))
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user_id(credentials=creds)

    assert exc_info.value.status_code == 401
