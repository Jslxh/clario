# Clario Docker Infrastructure

This directory contains container configurations and helpers for Clario's storage layer.

## Services

1. **PostgreSQL 16 (`clario-postgres`)**
   - Port: `5432`
   - Purpose: Enterprise relational storage (users, metadata, authorization policies, document metadata).
   - Health check: `pg_isready`

2. **Qdrant Vector Database (`clario-qdrant`)**
   - HTTP Port: `6333`
   - gRPC Port: `6334`
   - Purpose: High-dimensional vector indexing and fast similarity search for RAG embeddings.
   - Health check: `GET http://localhost:6333/healthz`

## Usage Commands

Start all data services in detached mode:
```bash
docker compose up -d
```

Check running containers:
```bash
docker compose ps
```

Stop services:
```bash
docker compose down
```
