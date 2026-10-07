from typing import List, Set, Optional, Any, Union
from pydantic import field_validator
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
        "http://localhost:5858",
        "http://127.0.0.1:5858",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple, set)):
            return [str(i).strip() for i in v if str(i).strip()]
        return v

    # Relational Database Settings (PostgreSQL)
    DATABASE_URL: str = "postgresql+psycopg://clario_user:clario_password@localhost:5432/clario_db"

    # Vector Database & Embedding Settings (Phase 5)
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
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

    # Cross-Encoder Reranking Configuration (Phase 8)
    RERANKING_ENABLED: bool = True
    RERANKING_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKING_BATCH_SIZE: int = 32
    RERANKING_DEVICE: str = "auto"
    RERANKING_CANDIDATE_POOL_SIZE: int = 20
    RERANKING_FALLBACK_ON_ERROR: bool = True



    # Document Storage & Upload Limits (Phase 2B)
    STORAGE_BACKEND: str = "local"         # Options: "local", "s3", "r2"
    STORAGE_DIR: str = "storage"
    MAX_UPLOAD_SIZE_BYTES: int = 52428800  # 50 MB max limit
    ALLOWED_EXTENSIONS: Set[str] = {"pdf", "docx", "txt"}

    # Cloud Object Storage (S3 / Cloudflare R2)
    S3_BUCKET_NAME: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None  # e.g., https://<account_id>.r2.cloudflarestorage.com
    S3_ACCESS_KEY_ID: Optional[str] = None
    S3_SECRET_ACCESS_KEY: Optional[str] = None
    S3_REGION_NAME: Optional[str] = "auto" # Cloudflare R2 default is "auto", AWS e.g. "us-east-1"

    # Document Chunking Configuration (Phase 4)
    CHUNK_SIZE: int = 500         # Target size in tokens (~2000 chars)
    CHUNK_OVERLAP: int = 75       # Overlap size in tokens (~300 chars)
    CHARS_PER_TOKEN: float = 4.0   # Isolated token estimation multiplier

    # Security & Authentication
    JWT_SECRET: str = "default-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # AI & LLM Provider Configuration (Phase 9)
    LLM_PROVIDER: str = "mock"             # Options: "mock", "openai", "azure", "ollama", "vllm"
    LLM_MODEL_NAME: str = "gpt-4o-mini"
    LLM_API_BASE_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_TIMEOUT_SECONDS: float = 30.0
    LLM_MAX_RETRIES: int = 2
    LLM_TEMPERATURE: float = 0.0           # Fixed deterministic temperature for enterprise facts
    LLM_MAX_OUTPUT_TOKENS: int = 1024
    LLM_CONTEXT_TOKEN_BUDGET: int = 4000
    LLM_MIN_RELEVANCE_SCORE: Optional[float] = None

    # Grounding & Faithfulness Verification Configuration (Phase 10)
    VERIFICATION_ENABLED: bool = False     # Default-off / opt-in
    VERIFICATION_MODEL_NAME: str = "cross-encoder/nli-deberta-v3-small"
    VERIFICATION_MAX_PAIRS: int = 20       # Global candidate-pair cap per query
    VERIFICATION_BATCH_SIZE: int = 16
    VERIFICATION_DEVICE: str = "auto"
    VERIFICATION_ENTAILMENT_THRESHOLD: float = 0.65
    VERIFICATION_CONTRADICTION_THRESHOLD: float = 0.55

    @property
    def sqlalchemy_database_url(self) -> str:
        """Ensure standard SQLAlchemy postgresql+psycopg driver URL format for PostgreSQL & Supabase/Neon/Render."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
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
