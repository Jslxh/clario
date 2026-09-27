from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator


class Settings(BaseSettings):
    PROJECT_NAME: str = "Clario Enterprise Knowledge Intelligence"
    SERVICE_NAME: str = "clario-backend"
    API_V1_STR: str = "/api/v1"
    
    # Environment & Server
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # Database Settings (PostgreSQL)
    DATABASE_URL: str = "postgresql://clario_user:clario_password@localhost:5432/clario_db"

    # Vector DB Settings (Qdrant)
    QDRANT_URL: str = "http://localhost:6333"

    # Security & Authentication Placeholder
    JWT_SECRET: str = "default-jwt-secret-key-change-in-production"

    # AI & LLM Placeholder
    LLM_API_KEY: str = "default-llm-api-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
