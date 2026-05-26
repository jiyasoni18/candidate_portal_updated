import logging

from livekit import api as livekit_api

from config import settings

logger = logging.getLogger(__name__)


class LiveKitProvisionError(Exception):
    """Raised when the LiveKit server fails to create a room."""


class LiveKitTokenError(Exception):
    """Raised when token generation fails."""


def _http_url(url: str) -> str:
    """Convert a wss:// or ws:// URL to https:// or http:// for REST API calls."""
    if url.startswith("wss://"):
        return "https://" + url[6:]
    if url.startswith("ws://"):
        return "http://" + url[5:]
    return url


async def provision_room(room_name: str, metadata: str) -> None:
    """Create a LiveKit room with the given metadata string injected,
    and dispatch the practice-interview-agent to it.

    Raises:
        LiveKitProvisionError: if the LiveKit server returns an error.
    """
    try:
        async with livekit_api.LiveKitAPI(
            url=_http_url(settings.LIVEKIT_API_URL),
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
        ) as lk:
            await lk.room.create_room(
                livekit_api.CreateRoomRequest(
                    name=room_name,
                    metadata=metadata,
                )
            )
            # Explicitly dispatch the agent to this room
            await lk.agent_dispatch.create_dispatch(
                livekit_api.CreateAgentDispatchRequest(
                    agent_name="practice-interview-agent",
                    room=room_name,
                    metadata=metadata,
                )
            )
    except Exception as exc:
        logger.error("LiveKit room provisioning failed for room %s: %s", room_name, exc)
        raise LiveKitProvisionError(str(exc)) from exc


async def generate_token(room_name: str, identity: str) -> str:
    """Return a signed JWT granting room_join, can_publish, and can_subscribe.

    Token generation is CPU-bound (JWT signing) but fast enough to run inline.

    Raises:
        LiveKitTokenError: if token generation fails.
    """
    try:
        token = (
            livekit_api.AccessToken(
                api_key=settings.LIVEKIT_API_KEY,
                api_secret=settings.LIVEKIT_API_SECRET,
            )
            .with_identity(identity)
            .with_grants(
                livekit_api.VideoGrants(
                    room=room_name,
                    room_join=True,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
        )
        return token.to_jwt()
    except Exception as exc:
        logger.error(
            "LiveKit token generation failed for room %s identity %s: %s",
            room_name,
            identity,
            exc,
        )
        raise LiveKitTokenError(str(exc)) from exc
