"""Tests for Settings config validation — Phase 7 requirement 6.3."""
import os
import pytest
from pydantic import ValidationError


def test_settings_raises_when_openai_api_key_missing(monkeypatch):
    """Settings must raise ValidationError if OPENAI_API_KEY is absent."""
    # Remove OPENAI_API_KEY from the environment if present
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    # Ensure the other required fields are present so only OPENAI_API_KEY is missing
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-secret")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter")
    monkeypatch.setenv("LIVEKIT_URL", "wss://localhost:7880")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram")
    monkeypatch.setenv("SARVAM_API_KEY", "test-sarvam")

    # Import Settings class (not the singleton) and instantiate fresh
    from pydantic_settings import BaseSettings, SettingsConfigDict

    # Re-import the class definition to get a fresh instance without .env interference
    import importlib
    import config as config_module

    # Reload to bypass module-level singleton; instantiate directly
    with pytest.raises(ValidationError) as exc_info:
        config_module.Settings(_env_file=None)  # type: ignore[call-arg]

    errors = exc_info.value.errors()
    missing_fields = [e["loc"][0] for e in errors if e["type"] == "missing"]
    assert "OPENAI_API_KEY" in missing_fields
