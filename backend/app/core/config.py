from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Relational Database Settings (PostgreSQL)
    DATABASE_URL: str = "postgresql+psycopg://clario_user:clario_password@localhost:5432/clario_db"

    # Vector Database Settings (Qdrant)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "clario_documents"
    QDRANT_VECTOR_SIZE: int = 384

    # Security & Authentication Placeholder
    JWT_SECRET: str = "default-jwt-secret-key-change-in-production"

    # AI & LLM Placeholder
    LLM_API_KEY: str = "default-llm-api-key"

    @property
    def sqlalchemy_database_url(self) -> str:
        """Ensure standard SQLAlchemy postgresql+psycopg driver URL format."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
