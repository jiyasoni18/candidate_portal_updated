import asyncpg
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from uuid import UUID

from config import settings

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_db(request: Request) -> asyncpg.Connection:
    """Acquire a connection from the app-level asyncpg pool."""
    async with request.app.state.db_pool.acquire() as conn:
        yield conn


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> UUID:
    """Decode the JWT from the Authorization: Bearer header and return the user UUID.

    Raises HTTP 401 for missing, expired, or invalid tokens.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(status_code=401, detail="Invalid token payload.")

    try:
        return UUID(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token payload.")
