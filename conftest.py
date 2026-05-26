"""Root conftest.py — sets required environment variables before any module is imported."""
import os

# Provide dummy keys so config.py doesn't raise ValidationError during test collection.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-placeholder")
os.environ.setdefault("LIVEKIT_API_KEY", "test-livekit-key")
os.environ.setdefault("LIVEKIT_API_SECRET", "test-livekit-secret-that-is-long-enough")
os.environ.setdefault("LIVEKIT_URL", "wss://localhost:7880")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("DEEPGRAM_API_KEY", "test-deepgram-key")
os.environ.setdefault("SARVAM_API_KEY", "test-sarvam-key")
