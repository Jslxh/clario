from typing import List, Set
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

    # Vector Database & Embedding Settings (Phase 5)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION_NAME: str = "clario_documents"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-small-en-v1.5"  # Locked 384-dimensional model
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DEVICE: str = "auto"
    QDRANT_VECTOR_SIZE: int = 384

    # Retrieval & Hybrid Search Configuration (Phase 6 & 7)
    RETRIEVAL_TOP_K: int = 5
    RETRIEVAL_MAX_TOP_K: int = 100
    RRF_K: int = 60                       # Reciprocal Rank Fusion smoothing constant
    DEFAULT_RETRIEVAL_MODE: str = "hybrid" # Options: "hybrid", "semantic", "bm25"



    # Document Storage & Upload Limits (Phase 2B)
    STORAGE_DIR: str = "storage"
    MAX_UPLOAD_SIZE_BYTES: int = 52428800  # 50 MB max limit
    ALLOWED_EXTENSIONS: Set[str] = {"pdf", "docx", "txt"}

    # Document Chunking Configuration (Phase 4)
    CHUNK_SIZE: int = 500         # Target size in tokens (~2000 chars)
    CHUNK_OVERLAP: int = 75       # Overlap size in tokens (~300 chars)
    CHARS_PER_TOKEN: float = 4.0   # Isolated token estimation multiplier

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
