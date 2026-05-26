"""Unit tests for api/livekit_helper.py — token claim structure.

Requirements: 4.1, 4.2, 4.3
"""
import pytest
import jwt

from api.livekit_helper import generate_token, LiveKitTokenError


ROOM_NAME = "practice-room-test-session-abc"
IDENTITY = "user-789"


@pytest.mark.asyncio
async def test_generate_token_returns_string():
    """generate_token returns a non-empty JWT string."""
    token = await generate_token(ROOM_NAME, IDENTITY)
    assert isinstance(token, str)
    assert len(token) > 0


@pytest.mark.asyncio
async def test_token_room_claim(monkeypatch):
    """JWT payload contains the correct 'room' claim (Requirement 4.2)."""
    token = await generate_token(ROOM_NAME, IDENTITY)
    # Decode without verification to inspect claims
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["video"]["room"] == ROOM_NAME


@pytest.mark.asyncio
async def test_token_identity_claim():
    """JWT 'sub' claim matches the provided identity (Requirement 4.2)."""
    token = await generate_token(ROOM_NAME, IDENTITY)
    payload = jwt.decode(token, options={"verify_signature": False})
    assert payload["sub"] == IDENTITY


@pytest.mark.asyncio
async def test_token_grants():
    """JWT video grants include room_join, can_publish, can_subscribe (Requirement 4.3)."""
    token = await generate_token(ROOM_NAME, IDENTITY)
    payload = jwt.decode(token, options={"verify_signature": False})
    video = payload["video"]
    assert video["roomJoin"] is True
    assert video["canPublish"] is True
    assert video["canSubscribe"] is True
