from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str = (
        "postgresql://practice_user:practice_password_2026@localhost:5434/interview_practice_db"
    )
    STORAGE_ROOT: str = "./storage/resumes"
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "google/gemini-2.0-flash-001"
    GRADING_MODEL: str = "google/gemini-2.0-flash-001"
    LIVEKIT_API_URL: str = "http://localhost:7880"
    LIVEKIT_API_KEY: str
    LIVEKIT_API_SECRET: str
    LIVEKIT_URL: str
    OPENAI_API_KEY: str
    DEEPGRAM_API_KEY: str
    SARVAM_API_KEY: str
    BACKEND_URL: str = "http://localhost:8000"
    JWT_SECRET_KEY: str = "changeme-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24


settings = Settings()
