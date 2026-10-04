from fastapi import APIRouter
from app.api.v1 import health, documents, search, query, auth, conversations, audit

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(documents.router, tags=["Documents"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(query.router, prefix="/query", tags=["Query & Generation"])
api_router.include_router(conversations.router, tags=["Conversations"])
api_router.include_router(audit.router, tags=["Audit Logs"])


