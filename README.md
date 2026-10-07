# Clario — Enterprise Knowledge Intelligence Platform

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8.3-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16.0-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Qdrant](https://img.shields.io/badge/Qdrant-1.10%2B-DC382D.svg?logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![SQLAlchemy 2.x](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00.svg)](https://www.sqlalchemy.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Clario is an enterprise-grade Knowledge Intelligence and Retrieval-Augmented Generation (RAG) platform. It provides authenticated enterprise users with a secure, department-governed knowledge engine that retrieves authorized internal documentation, synthesizes answers through modern Large Language Models, maps source citations to document chunks, and verifies factual faithfulness using Natural Language Inference (NLI).

---

## Table of Contents

- [1. Project Status](#1-project-status)
- [2. Problem Statement & Why Clario Exists](#2-problem-statement--why-clario-exists)
- [3. Core Capabilities](#3-core-capabilities)
- [4. Architectural Workflows & Diagrams](#4-architectural-workflows--diagrams)
  - [4.1 High-Level System Architecture](#41-high-level-system-architecture)
  - [4.2 End-to-End RAG Workflow](#42-end-to-end-rag-workflow)
  - [4.3 Document Ingestion & Indexing Pipeline](#43-document-ingestion--indexing-pipeline)
  - [4.4 Hybrid Retrieval & Reranking Architecture](#44-hybrid-retrieval--reranking-architecture)
  - [4.5 Security Boundary & RBAC Filtering Flow](#45-security-boundary--rbac-filtering-flow)
  - [4.6 Grounding & Faithfulness Verification Flow](#46-grounding--faithfulness-verification-flow)
  - [4.7 Database Entity-Relationship Architecture](#47-database-entity-relationship-architecture)
- [5. Technology Stack](#5-technology-stack)
- [6. System Components](#6-system-components)
- [7. Repository Structure](#7-repository-structure)
- [8. Database & Storage Architecture](#8-database--storage-architecture)
- [9. Authentication & Authorization (RBAC)](#9-authentication--authorization-rbac)
- [10. Document Processing Pipeline](#10-document-processing-pipeline)
- [11. Retrieval Architecture](#11-retrieval-architecture)
- [12. Cross-Encoder Reranking](#12-cross-encoder-reranking)
- [13. Context Construction & Prompt Containment](#13-context-construction--prompt-containment)
- [14. LLM Generation & Provider Interface](#14-llm-generation--provider-interface)
- [15. Grounding & Faithfulness Verification](#15-grounding--faithfulness-verification)
- [16. Citation Mapping & Sanitization](#16-citation-mapping--sanitization)
- [17. Multi-Turn Conversations](#17-multi-turn-conversations)
- [18. Enterprise Audit Logging](#18-enterprise-audit-logging)
- [19. API Reference](#19-api-reference)
- [20. Frontend Interface](#20-frontend-interface)
- [21. Evaluation Strategy & Benchmark Suite](#21-evaluation-strategy--benchmark-suite)
- [22. Test Suite & Verification](#22-test-suite--verification)
- [23. Installation & Local Setup](#23-installation--local-setup)
- [24. Environment Configuration](#24-environment-configuration)
- [25. Security & Governance Notes](#25-security--governance-notes)
- [26. Known Limitations](#26-known-limitations)
- [27. Future Roadmap](#27-future-roadmap)
- [28. License](#28-license)

---

## 1. Project Status

Clario has achieved full implementation across Milestones 1 through 11:
- **Core Platform & Storage**: Relational schema (PostgreSQL 16 via SQLAlchemy 2.x & Alembic) and vector engine (Qdrant 1.10+).
- **Security & RBAC**: JWT HMAC-SHA256 bearer tokens, PBKDF2-HMAC-SHA256 password hashing, three system roles (`admin`, `analyst`, `user`), and department-level document isolation.
- **Document Ingestion**: Multi-format extraction (PDF, DOCX, TXT), recursive structural chunking preserving headers and page numbers, and asynchronous background processing.
- **Retrieval Engine**: Dual-stream hybrid search combining dense semantic embeddings (`BAAI/bge-small-en-v1.5`), BM25Okapi keyword search, Reciprocal Rank Fusion ($k=60$), and second-stage neural reranking (`cross-encoder/ms-marco-MiniLM-L-6-v2`).
- **Generation & Trust**: Context budgeting, prompt injection containment, OpenAI-compatible provider abstraction, inline citation mapping, and post-generation NLI claim verification (`cross-encoder/nli-deberta-v3-small`).
- **Conversations & Governance**: Multi-turn dialogue persistence with conversation ownership isolation, follow-up query contextualization, and automated sensitive-key-scrubbed audit logging.
- **Client Application**: React 19 + Vite dashboard featuring authenticated routing, document upload, status tracking, metadata exploration, and chunk inspection.

---

## 2. Problem Statement & Why Clario Exists

### The Enterprise Knowledge Challenge
Modern enterprises maintain thousands of operational guidelines, technical manuals, HR policies, and compliance briefs across fragmented document repositories. Standard enterprise search tools and naive generative AI implementations introduce severe organizational risks:

1. **Information Leakage Across Roles & Departments**: General-purpose AI chatbots lack server-side authorization boundaries. When indexed naively, confidential financial projections or sensitive HR compensation details leak to unauthorized personnel through conversational prompts.
2. **Hallucination & Ungrounded Claims**: Standard Large Language Models produce plausible but factually incorrect assertions when answering corporate questions. In enterprise operations, an ungrounded policy interpretation can result in regulatory penalties or contract breaches.
3. **Lack of Traceability & Attribution**: Answers generated without granular, verifiable citations prevent employees from validating facts against canonical documents.
4. **Retrieval Blindspots**: Semantic dense embeddings alone struggle with exact alphanumeric strings, error codes, and compliance identifiers (e.g., `POL-HR-2026-A` or `ERR-DB-504`), while keyword search fails on semantic paraphrasing.

### The Clario Solution
Clario solves these challenges through a **governed, verifiable intelligence pipeline**:
- **Strict Server-Side Security Authority**: Security boundaries are enforced in the database and retrieval service before documents ever reach the reranker, context constructor, or LLM.
- **Hybrid Retrieval + Neural Reranking**: Combines dense semantic vectors with lexical BM25 search via Reciprocal Rank Fusion ($k=60$) and cross-attention reranking, ensuring high recall on conceptual questions and exact precision on technical codes.
- **NLI-Based Grounding Verification**: Evaluates atomic claims against retrieved evidence using a DeBERTa cross-encoder, classifying outputs into deterministically audited faithfulness statuses.
- **Audited Lineage & Citation Integrity**: Maps generated statements directly to document chunks (including page, section, and department metadata) while automatically stripping unverified tags.

---

## 3. Core Capabilities

| Capability | Specification | Architectural Function |
| :--- | :--- | :--- |
| **Enterprise RBAC & Document Isolation** | 3 System Roles (`admin`, `analyst`, `user`) + 4 Document Access Levels (`public`, `internal`, `confidential`, `restricted`). | Enforces strict department and role boundaries at the database query layer prior to retrieval scoring. |
| **Structural Recursive Chunking** | Separator hierarchy (`\n\n`, `\n`, `. `, `; `, `, `, ` `) targeting 500 tokens with 75-token overlap. | Preserves document structure, headings, section context, start page, and end page boundaries without slicing words. |
| **Dense Semantic Vector Search** | `BAAI/bge-small-en-v1.5` 384-dimensional normalized embeddings indexed in Qdrant with Cosine distance. | Captures semantic intent and conceptual paraphrasing across enterprise documents. |
| **Lexical Keyword Search** | Rebuildable in-memory BM25Okapi index over canonical PostgreSQL chunk text. | Captures exact technical codes, policy identifiers, and acronyms that dense embeddings overlook. |
| **Reciprocal Rank Fusion (RRF)** | $RRF(d) = \sum_{r} \frac{1}{60 + \text{rank}_r(d)}$ with deterministic tie-breaking. | Merges dense and sparse retrieval ranks into a unified candidate pool without requiring score normalization. |
| **Cross-Encoder Neural Reranking** | `cross-encoder/ms-marco-MiniLM-L-6-v2` scoring query-chunk candidate pairs. | Re-scores first-stage candidates via deep cross-attention, surfacing the most relevant evidence chunks. |
| **Prompt Injection Containment** | Passive `<enterprise_context>` containment tags, character escaping, and deterministic system prompts. | Treats retrieved documents as untrusted data, preventing document-embedded instruction overrides. |
| **Inline Citation Mapping** | Deterministic `[Doc-N]` extraction mapping to PostgreSQL UUIDs, page ranges, and sections. | Provides verifiable source attribution and strips hallucinated citation references. |
| **Grounding & Faithfulness Verification** | Post-generation NLI checking via `cross-encoder/nli-deberta-v3-small`. | Classifies claims as `SUPPORTED`, `CONTRADICTED`, `INSUFFICIENT`, or `UNVERIFIED` with answer-level status derivation. |
| **Multi-Turn Contextualization** | Ownership-isolated conversation sessions with history-aware retrieval query reformulation. | Maintains conversational continuity across follow-up queries while preventing cross-user session leakage. |
| **Governance Audit Ledger** | Structured PostgreSQL audit table with automatic sensitive-key redaction. | Logs authentication, uploads, deletions, searches, and queries with IP and user metadata. |

---

## 4. Architectural Workflows & Diagrams

### 4.1 High-Level System Architecture

```mermaid
flowchart TB
    subgraph CLIENT ["Client Layer"]
        UI["React 19 + Vite Frontend SPA"]
    end

    subgraph API_GATEWAY ["FastAPI Application Gateway"]
        AuthMiddleware["JWT Bearer Authentication & RBAC Guard"]
        APIRouter["API Router (/api/v1)"]
    end

    subgraph CORE_SERVICES ["Enterprise Core Services"]
        DocService["Document Ingestion & Storage Service"]
        Retriever["Hybrid Retriever (Semantic + BM25 + RRF)"]
        Reranker["Cross-Encoder Neural Reranker"]
        ContextBuilder["Context Construction & Token Budgeter"]
        LLM["LLM Provider (OpenAI / Azure / Ollama / Mock)"]
        Verifier["NLI Grounding Verification Service"]
        ConvService["Conversation & History Service"]
        AuditService["Enterprise Audit Logging Service"]
    end

    subgraph STORAGE_LAYER ["Persistence & Storage Layer"]
        PG[("PostgreSQL 16 (Relational Metadata & Canonical Chunks)")]
        Qdrant[("Qdrant Vector DB (384-d Cosine Embeddings)")]
        FileStore[("File Storage (Local Storage / S3 / R2)")]
    end

    UI --> AuthMiddleware
    AuthMiddleware --> APIRouter
    APIRouter --> DocService
    APIRouter --> Retriever
    APIRouter --> ConvService
    APIRouter --> AuditService

    DocService --> FileStore
    DocService --> PG
    DocService --> Qdrant

    Retriever --> Qdrant
    Retriever --> PG
    Retriever --> Reranker

    Reranker --> ContextBuilder
    ContextBuilder --> LLM
    LLM --> Verifier
    Verifier --> ConvService
    ConvService --> PG
    AuditService --> PG
```

---

### 4.2 End-to-End RAG Workflow

```mermaid
sequenceDiagram
    autonumber
    actor User as Authenticated User
    participant Gateway as FastAPI Router
    participant Auth as RBAC Security Guard
    participant Retrieval as Hybrid Retriever
    participant VectorDB as Qdrant Vector DB
    participant SQL as PostgreSQL
    participant Rerank as Cross-Encoder Reranker
    participant Ctx as Context Builder
    participant Model as LLM Generation
    participant NLI as NLI Verifier
    participant Audit as Audit Service

    User->>Gateway: POST /api/v1/query (query, filters, top_k)
    Gateway->>Auth: Validate JWT & User Roles/Department
    Auth-->>Gateway: Authenticated User Context

    Gateway->>Retrieval: search(query, mode=hybrid, user=user)
    par Candidate Retrieval
        Retrieval->>VectorDB: Query BGE-small Embeddings (Cosine Top-K)
        Retrieval->>SQL: Query In-Memory BM25 Index
    end
    Retrieval->>Retrieval: Reciprocal Rank Fusion (k=60)
    Retrieval->>SQL: Hydrate Chunks + Enforce DB Authorization Filter
    Note over Retrieval,SQL: Unauthorized chunks dropped before reranking

    Retrieval->>Rerank: Score (Query, Chunk) Pairs
    Rerank-->>Retrieval: Ranked Candidates + Rerank Logits

    Retrieval-->>Gateway: Filtered, Ranked Chunks
    Gateway->>Ctx: build_context(query, candidates, history)
    Ctx-->>Gateway: Token-Budgeted Prompt & [Doc-N] XML Context

    Gateway->>Model: generate(system_prompt, user_prompt, temp=0.0)
    Model-->>Gateway: Raw Synthesized Answer

    opt Verification Enabled
        Gateway->>NLI: verify_generation(raw_answer, context_chunks)
        NLI->>NLI: Extract Claims -> Prioritize Pairs -> Predict NLI
        NLI-->>Gateway: VerificationResult (Faithfulness Status & Scores)
    end

    Gateway->>Gateway: Map Valid Citations & Strip Hallucinated Tags
    Gateway->>Audit: Log Query Event (Sanitized Telemetry)
    Gateway-->>User: GenerationResponse (Answer, Citations, Verification, Latency)
```

---

### 4.3 Document Ingestion & Indexing Pipeline

```mermaid
flowchart TD
    A["File Upload (PDF, DOCX, TXT)"] --> B{"Validation Gate"}
    B -- "Invalid Extension / Corrupt Magic Bytes / >50MB" --> C["HTTP 400 Bad Request"]
    B -- "Valid" --> D["Sanitize Filename & Save Original to Storage"]
    D --> E["Insert PostgreSQL Document Record (Status: UPLOADED)"]
    E --> F["Enqueue FastAPI BackgroundTask"]
    F --> G["Transition Document Status: PROCESSING"]
    G --> H{"Parser Factory"}
    H -- "PDF" --> I["pypdf: Page Boundaries & Lineage"]
    H -- "DOCX" --> J["python-docx: Paragraphs, Headings, Tables"]
    H -- "TXT" --> K["UTF-8 / Latin-1 Robust Reader"]
    I --> L["Recursive Structural Chunker<br/>(500 tokens, 75 overlap, paragraph -> line -> sentence)"]
    J --> L
    K --> L
    L --> M["Transaction: Persist DocumentChunk Rows to PostgreSQL"]
    M --> N["Batch BGE-small Embeddings Generation (384-d, batch_size=32)"]
    N --> O["Idempotent Upsert Points to Qdrant (clario_documents)"]
    O --> P["Post-Commit: Update In-Memory BM25 Index"]
    P --> Q["Transition Document Status: READY"]
    Q --> R["Record Audit Log (Action: process, Resource: document)"]

    style C fill:#f8d7da,stroke:#f5c6cb
    style Q fill:#d4edda,stroke:#c3e6cb
```

---

### 4.4 Hybrid Retrieval & Reranking Architecture

```mermaid
flowchart LR
    subgraph INPUT ["Search Query"]
        Q["User Query Text"]
    end

    subgraph STAGE_1 ["First-Stage Candidate Retrieval"]
        direction TB
        subgraph DENSE ["Dense Stream"]
            E["Query Embedding\nBAAI/bge-small-en-v1.5"] --> V["Qdrant Search\nCosine Distance"]
        end
        subgraph SPARSE ["Sparse Stream"]
            T["Tokenize Identifier Regex"] --> B["BM25Okapi Search\nToken Match"]
        end
        V --> RRF["Reciprocal Rank Fusion\nRRF(d) = Σ 1 / (60 + rank)"]
        B --> RRF
    end

    subgraph SECURITY_GATE ["Server-Side Authorization Boundary"]
        RRF --> HYD["PostgreSQL Batch Hydration"]
        HYD --> AUTH{"Authorized for User?"}
        AUTH -- "No" --> DROP["Drop Chunk (Zero Leakage)"]
        AUTH -- "Yes" --> POOL["Authorized Candidate Pool"]
    end

    subgraph STAGE_2 ["Second-Stage Neural Reranking"]
        POOL --> CE["Cross-Encoder\nms-marco-MiniLM-L-6-v2\nCross-Attention (Query, Content)"]
        CE --> SORT["Deterministic Descending Sort"]
        SORT --> TOP["Top-K Evaluated Candidates"]
    end

    Q --> E
    Q --> T
    Q --> CE

    style DROP fill:#f8d7da,stroke:#f5c6cb
    style TOP fill:#d4edda,stroke:#c3e6cb
```

---

### 4.5 Security Boundary & RBAC Filtering Flow

```mermaid
flowchart TD
    UserReq["Incoming Query / Search Request"] --> TokenCheck{"Valid JWT Bearer Token?"}
    TokenCheck -- "No Token" --> Unauth["Role: Unauthenticated User"]
    TokenCheck -- "Valid Token" --> ParseUser["Extract User, Roles, Department"]

    Unauth --> FilterRule1["Access Filter: access_level == 'public'"]
    
    ParseUser --> RoleCheck{"Check Assigned Roles"}
    RoleCheck -- "admin" --> FilterRuleAdmin["Access Filter: Unrestricted (All Documents)"]
    RoleCheck -- "analyst" --> FilterRuleAnalyst["Access Filter:\naccess_level == 'public' OR\n(access_level IN ['internal', 'confidential'] AND\n(doc.dept == user.dept OR doc.dept IS NULL))"]
    RoleCheck -- "user" --> FilterRuleUser["Access Filter:\naccess_level == 'public' OR\n(access_level == 'internal' AND (doc.dept == user.dept OR doc.dept IS NULL OR doc.uploaded_by == user.id)) OR\ndoc.uploaded_by == user.id"]

    FilterRule1 --> ExecuteSQL["Execute PostgreSQL Query / Filter Hydrated Chunks"]
    FilterRuleAdmin --> ExecuteSQL
    FilterRuleAnalyst --> ExecuteSQL
    FilterRuleUser --> ExecuteSQL

    ExecuteSQL --> SafeContext["Candidate Chunks Guaranteed Authorized"]
    SafeContext --> Downstream["Downstream: Reranking -> Context -> LLM"]

    style Downstream fill:#d4edda,stroke:#c3e6cb
```

---

### 4.6 Grounding & Faithfulness Verification Flow

```mermaid
flowchart TD
    A["Raw LLM Generated Output"] --> B{"Has Sufficient Context?"}
    B -- "No" --> C["Status: INSUFFICIENT_EVIDENCE\n(Faithfulness Score: None)"]
    B -- "Yes" --> D["Claim Extractor\n(Sentence & Clause Splitting)"]
    D --> E{"Total Claims > 0?"}
    E -- "No" --> F["Status: NO_CLAIMS_FOUND\n(Faithfulness Score: None)"]
    E -- "Yes" --> G["Candidate Pair Prioritization\n(Tier 1: Explicit Citation Tag\nTier 2: Token Overlap Jaccard\nTier 3: Context Rank)"]
    G --> H["Apply Global Cap: VERIFICATION_MAX_PAIRS (20)"]
    H --> I["Batch Cross-Encoder NLI Inference\ncross-encoder/nli-deberta-v3-small"]
    I --> J["Compute Probabilities: Entailment, Contradiction, Neutral"]
    J --> K["Score Atomic Claims against Thresholds\nEntailment >= 0.65 | Contradiction >= 0.55"]
    K --> L["Assign Claim Labels:\nSUPPORTED | CONTRADICTED | INSUFFICIENT | UNVERIFIED"]
    L --> M{"Evaluate Answer Status Precedence"}
    M -- ">=1 Claim Contradicted" --> N["Status: CONTRADICTED"]
    M -- "100% Supported & Fully Evaluated" --> O["Status: VERIFIED_FAITHFUL\n(Faithfulness Score: 1.0)"]
    M -- ">=1 Supported, 0 Contradicted" --> P["Status: PARTIALLY_SUPPORTED\n(Score: supported / total)"]
    M -- "0 Supported, >=1 Unverified" --> Q["Status: INCOMPLETE_VERIFICATION\n(Score: 0.0)"]
    M -- "100% Insufficient" --> R["Status: UNSUPPORTED\n(Score: 0.0)"]

    style O fill:#d4edda,stroke:#c3e6cb
    style N fill:#f8d7da,stroke:#f5c6cb
    style P fill:#fff3cd,stroke:#ffeeba
```

---

### 4.7 Database Entity-Relationship Architecture

```mermaid
erDiagram
    User ||--o{ user_roles : "assigned"
    Role ||--o{ user_roles : "mapped_to"
    User ||--o{ Document : "uploads"
    User ||--o{ Conversation : "owns"
    User ||--o{ AuditLog : "triggers"
    Document ||--o{ DocumentChunk : "contains"
    Conversation ||--o{ Message : "contains"

    User {
        UUID id PK
        String email UK
        String name
        String password_hash
        String department
        Boolean is_active
        DateTime created_at
        DateTime updated_at
    }

    Role {
        UUID id PK
        String name UK
        Text description
    }

    user_roles {
        UUID user_id PK, FK
        UUID role_id PK, FK
    }

    Document {
        UUID id PK
        String filename
        String title
        String document_type
        String department
        String access_level
        String file_path
        BigInteger file_size
        Enum status
        UUID uploaded_by FK
        DateTime created_at
        DateTime updated_at
    }

    DocumentChunk {
        UUID id PK
        UUID document_id FK
        Integer chunk_index
        Text content
        Integer page_number
        Integer end_page
        String section
        DateTime created_at
    }

    Conversation {
        UUID id PK
        UUID user_id FK
        String title
        DateTime created_at
        DateTime updated_at
    }

    Message {
        UUID id PK
        UUID conversation_id FK
        String role
        Text content
        String verification_status
        DateTime created_at
        DateTime updated_at
    }

    AuditLog {
        UUID id PK
        UUID user_id FK
        String action
        String resource_type
        String resource_id
        JSONB details
        DateTime created_at
    }
```

---

## 5. Technology Stack

| Layer | Component | Version / Specification | Rationale |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | FastAPI | 0.110+ | Asynchronous REST endpoints, native OpenAPI schema generation, Pydantic v2 validation. |
| **Language Runtime** | Python | 3.11+ (tested on 3.12 / 3.14) | Type-hinted asynchronous ecosystem with native ML library support. |
| **Relational Database** | PostgreSQL | 16-alpine | Canonical enterprise storage, transactional ACID integrity, relational constraints, JSONB audit logging. |
| **ORM & Migrations** | SQLAlchemy & Alembic | 2.0+ & 1.13+ | Declarative typed models (`Mapped`), automated migrations, connection pooling via `psycopg`. |
| **Vector Database** | Qdrant | 1.10+ | Embedded vector indexing, HNSW cosine similarity search, payload metadata filtering, gRPC/HTTP interface. |
| **Dense Embeddings** | Sentence Transformers | `BAAI/bge-small-en-v1.5` | High-accuracy 384-dimensional dense embeddings, optimized for retrieval speed and low memory footprint. |
| **Sparse Lexical Search** | rank_bm25 | BM25Okapi | Exact keyword matching, term-frequency inverted index over canonical database chunks. |
| **Reranking Engine** | Sentence Transformers | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Deep cross-attention reranking of top candidate pairs, outperforming bi-encoder cosine ranking. |
| **NLI Verifier** | Sentence Transformers | `cross-encoder/nli-deberta-v3-small` | Natural Language Inference (Entailment, Contradiction, Neutral) for claim verification. |
| **Document Parsers** | pypdf, python-docx | Latest stable | Native extraction of text, page markers, paragraphs, and headings without cloud dependencies. |
| **LLM Provider** | OpenAI API Client | `gpt-4o-mini` / Compatible | Structured question answering; provider abstraction supports OpenAI, Azure, Ollama, and Mock. |
| **Frontend Framework** | React | 19.2 | High-performance user interface, hooks-driven state, concurrent rendering. |
| **Frontend Tooling** | Vite | 8.3 | Instant HMR development server, ES module bundler. |
| **Styling** | Custom Enterprise CSS | Vanilla CSS | Low-latency, zero-dependency enterprise design system with dark-slate typography and status indicators. |
| **Testing** | Pytest & Node Test | Pytest 8.x & Node 18+ | 23 backend test modules verifying every component; unit tests for frontend client. |
| **Containerization** | Docker & Compose | Compose v2 | Local containerized orchestration for PostgreSQL and Qdrant. |

---

## 6. System Components

The Clario monorepo is partitioned into clear functional subsystems:

1. **`clario-backend`**: FastAPI application exposing the REST API surface under `/api/v1` and root health endpoints.
2. **`clario-db`**: PostgreSQL 16 container managing relational users, roles, documents, chunks, conversations, and audit records.
3. **`clario-qdrant`**: Qdrant vector database container managing high-dimensional vector embeddings for document chunks.
4. **`clario-frontend`**: React 19 single-page application providing authenticated document management and identity telemetry.
5. **`clario-storage`**: File storage abstraction managing physical binary assets (`storage/documents/<uuid>/original.<ext>`) with local disk, AWS S3, and Cloudflare R2 drivers.

---

## 7. Repository Structure

```text
clario/
├── docker-compose.yml                 # PostgreSQL 16 and Qdrant 1.10 container orchestration
├── .env.example                       # Canonical environment variable configuration template
├── .gitignore                         # Version control exclusions
├── README.md                          # Comprehensive project technical documentation
├── PRD.md                             # Enterprise Product Requirements Document
│
├── docker/                            # Docker configurations and operational guides
│   └── README.md                      # Container health checks, ports, and operational notes
│
├── backend/                           # FastAPI Backend Application
│   ├── requirements.txt               # Locked Python package dependencies
│   ├── alembic.ini                    # Alembic database migration configuration
│   ├── alembic/                       # Database schema version migrations
│   │   ├── env.py                     # Migration runner with SQLAlchemy model registration
│   │   └── versions/
│   │       ├── 439da9f4d286_initial_core_database_schema_setup.py
│   │       └── e8f7c1f752f4_add_end_page_column_to_document_chunks.py
│   ├── app/
│   │   ├── main.py                    # Application entrypoint, CORS, and root health check
│   │   ├── core/                      # Settings, database engine, security, and exceptions
│   │   │   ├── config.py              # Pydantic Settings configuration loader
│   │   │   ├── database.py            # SQLAlchemy engine and SessionLocal dependency
│   │   │   ├── security.py            # PBKDF2 password hashing & HMAC-SHA256 JWT tokens
│   │   │   └── exceptions.py          # Domain-specific exception hierarchy
│   │   ├── models/                    # SQLAlchemy declarative relational models
│   │   │   ├── base.py                # TimestampMixin (created_at, updated_at)
│   │   │   ├── user.py                # User model and user_roles association table
│   │   │   ├── role.py                # Role model and system role constants
│   │   │   ├── document.py            # Document model and DocumentStatus enum
│   │   │   ├── document_chunk.py      # DocumentChunk model with page/section lineage
│   │   │   ├── conversation.py        # Conversation and Message models
│   │   │   └── audit_log.py           # AuditLog model with JSONB details
│   │   ├── schemas/                   # Pydantic v2 validation and serialization schemas
│   │   │   ├── auth.py, user.py       # Authentication, registration, and user profiles
│   │   │   ├── document.py, chunk.py  # Document and chunk metadata schemas
│   │   │   ├── vector.py              # Qdrant payload schema
│   │   │   ├── generation.py          # RAG request, response, and citation schemas
│   │   │   ├── verification.py        # Claim verification and faithfulness schemas
│   │   │   ├── conversation.py        # Multi-turn conversation and message schemas
│   │   │   └── audit.py               # Governance audit log schemas
│   │   ├── api/                       # API router registrations and dependencies
│   │   │   ├── deps.py                # Authentication and require_roles RBAC guards
│   │   │   ├── router.py              # Aggregated v1 API router
│   │   │   └── v1/                    # Versioned REST endpoints
│   │   │       ├── health.py          # System and database connectivity health check
│   │   │       ├── auth.py            # Register, login, and current-user endpoints
│   │   │       ├── documents.py       # Upload, process, list, get, and delete documents
│   │   │       ├── search.py          # Standalone hybrid/semantic/BM25 document search
│   │   │       ├── query.py           # End-to-end RAG question answering endpoint
│   │   │       ├── conversations.py   # Multi-turn dialogue sessions and messages
│   │   │       └── audit.py           # Governance audit log retrieval
│   │   └── services/                  # Business logic services
│   │       ├── file_storage.py        # Local/S3/R2 storage abstraction
│   │       ├── document_service.py    # Document lifecycle and authorization checks
│   │       ├── indexing_service.py    # Batch vector embedding and Qdrant indexing
│   │       ├── audit_service.py       # Structured audit event logging & redaction
│   │       ├── conversation_service.py# Session management, isolation, and query contextualization
│   │       ├── parsers/               # PDF (pypdf), DOCX (python-docx), TXT parsers
│   │       ├── chunking/              # Recursive structural chunker & token counters
│   │       ├── embeddings/            # SentenceTransformer BGE-small embedding service
│   │       ├── vector_store/          # Qdrant vector store adapter
│   │       ├── retrieval/             # Semantic, BM25, RRF fusion, and evaluation
│   │       ├── reranking/             # Cross-Encoder neural reranker
│   │       ├── context/               # Token budgeter & prompt containment builder
│   │       ├── llm/                   # OpenAI-compatible provider & deterministic mock
│   │       ├── verification/          # Claim extraction & NLI DeBERTa verification
│   │       └── generation/            # End-to-end Q&A generation orchestration
│   └── tests/                         # Pytest test suite (23 comprehensive modules)
│
└── frontend/                          # React 19 + Vite Enterprise Client
    ├── index.html                     # HTML root template
    ├── package.json                   # React 19 dependencies & scripts
    ├── vite.config.js                 # Vite development server configuration
    ├── src/
    │   ├── main.jsx                   # React application mount
    │   ├── App.jsx                    # Root view routing (auth vs workspace)
    │   ├── index.css, App.css         # Enterprise typography and layout styles
    │   ├── api/
    │   │   └── client.js              # Fetch-based API client with JWT bearer injection
    │   ├── context/
    │   │   └── AuthContext.jsx        # Authentication state, login, and session persistence
    │   ├── components/
    │   │   ├── Login.jsx, Register.jsx# User authentication forms
    │   │   ├── Dashboard.jsx          # Identity, token, and system health status
    │   │   ├── ProtectedRoute.jsx     # Client-side route guard
    │   │   ├── layout/AppLayout.jsx   # Header, sidebar navigation, and footer layout
    │   │   └── documents/             # Document management UI components
    │   │       ├── DocumentTable.jsx  # Paginated document table
    │   │       ├── DocumentUploadModal.jsx # Upload dialog with department/access selection
    │   │       ├── DocumentDetailsDrawer.jsx # Detail drawer with chunk inspection
    │   │       ├── DocumentStatusBadge.jsx # Color-coded status indicator
    │   │       ├── DocumentFilters.jsx# Department and status filters
    │   │       └── ChunkViewer.jsx    # Viewer for document chunk contents
    │   └── pages/
    │       └── Documents.jsx          # Main enterprise documents management view
    └── tests/
        └── document_management.test.js# Node-based API client unit tests
```

---

## 8. Database & Storage Architecture

### Relational Schema (PostgreSQL 16)
PostgreSQL is the canonical source of truth for all enterprise metadata, authorization boundaries, canonical chunk content, and conversation history:

- **`users`**: User identity, unique email, password hash, assigned department, and activation status.
- **`roles`**: System role definitions (`admin`, `analyst`, `user`).
- **`user_roles`**: Many-to-many junction mapping users to roles with cascade deletion.
- **`documents`**: Document identity, sanitized filename, title, document type (`pdf`, `docx`, `txt`), department, access level (`public`, `internal`, `confidential`, `restricted`), physical file path, byte size, processing status (`uploaded`, `processing`, `ready`, `failed`), and uploader reference.
- **`document_chunks`**: Canonical text content, parent document reference (cascade deletion), sequential `chunk_index`, starting `page_number`, ending `end_page`, and section header string. Enforces unique constraint `(document_id, chunk_index)`.
- **`conversations`**: Multi-turn sessions owned by a specific `user_id` with timestamps.
- **`messages`**: Dialogue history (`role`, `content`, `verification_status`) linked to parent conversation.
- **`audit_logs`**: Security audit records (`user_id`, `action`, `resource_type`, `resource_id`, `details` JSONB, `created_at`).

### Vector Storage (Qdrant 1.10+)
Qdrant manages dense vector representations for similarity search:
- **Collection Name**: `clario_documents`
- **Vector Dimension**: 384 dimensions (`BAAI/bge-small-en-v1.5`)
- **Distance Metric**: Cosine similarity (`qmodels.Distance.COSINE`)
- **Point Identifier**: The UUID of the corresponding `document_chunks` record in PostgreSQL.
- **Payload Schema**: Indexed attributes (`document_id`, `chunk_id`, `page_number`, `end_page`, `section`, `department`, `document_type`, `access_level`, `filename`).

### Physical Document Storage
Original uploaded files are persisted separately from relational tables using the `FileStorageService` abstraction:
- **Local Storage (`STORAGE_BACKEND=local`)**: Structured directory tree at `storage/documents/<document_id>/original.<ext>`.
- **Cloud Storage (`STORAGE_BACKEND=s3` / `STORAGE_BACKEND=r2`)**: S3-compatible bucket storage (AWS S3 or Cloudflare R2) configured via endpoint and access keys.

---

## 9. Authentication & Authorization (RBAC)

### Password Hashing & Token Issuance
- **Password Hashing**: PBKDF2-HMAC-SHA256 with 100,000 iterations and a cryptographically generated 16-byte random salt, stored as `salt$hash`.
- **Bearer Tokens**: Signed HMAC-SHA256 JWT tokens containing `sub` (user UUID), `email`, `roles`, `department`, `iat`, and `exp`. Token expiration defaults to 24 hours.

### The Three Application Roles
Clario defines exactly three application roles. There is no Auditor role:

| Role | Permissions & Capabilities | Explicit Restrictions |
| :--- | :--- | :--- |
| **USER** | - Use Knowledge Chat & multi-turn conversations<br/>- Search authorized company knowledge<br/>- Access public documents and internal documents matching their department<br/>- Access documents uploaded by themselves<br/>- View citations & grounding verification details<br/>- View own profile & logout | - Cannot manage users or assign roles<br/>- Cannot manage access permissions or company-wide metadata<br/>- Cannot edit, delete, or process arbitrary documents<br/>- Cannot access audit logs<br/>- Cannot view unauthorized departments or confidential documents |
| **ANALYST** | - Use Knowledge Chat & multi-turn conversations<br/>- Search authorized company knowledge<br/>- Access public, internal, and confidential documents within their department<br/>- Access global department-less documents<br/>- View citations & grounding verification details<br/>- View governance audit logs via `GET /api/v1/audit-logs` | - Cannot create or manage users<br/>- Cannot assign or change user roles<br/>- Cannot perform administrative system configurations<br/>- Cannot access documents belonging to other departments<br/>- Cannot perform unrestricted company-wide document operations |
| **ADMIN** | - Full, unrestricted access to company knowledge across all departments<br/>- Upload, process, and delete documents across all departments<br/>- Manage users and user roles<br/>- Access governance audit logs<br/>- Use Knowledge Chat, search, citations, and verification | - Subject to audit logging for all administrative operations |

### Server-Side Security Authority & Pre-Filtering
> [!IMPORTANT]
> The frontend is never treated as a security boundary. Document authorization filtering is enforced on the server before candidates enter the reranker, context builder, or LLM prompt.

When a query is executed, candidate chunks retrieved from Qdrant and BM25 are hydrated against PostgreSQL. During hydration, each chunk's parent document is evaluated against the authenticated user:

```python
# Server-side authorization check applied during hydration before reranking:
if not is_user_authorized_for_doc(user, doc):
    continue  # Excluded from candidate pool immediately
```

Unauthorized chunks are dropped immediately. They never appear in the candidate pool, never receive a reranking score, and never enter the prompt context.

---

## 10. Document Processing Pipeline

### Supported Formats
- **PDF (`.pdf`)**: Extracted via `pypdf.PdfReader`. Preserves original page numbers, page boundaries, and extracted text blocks.
- **DOCX (`.docx`)**: Extracted via `python-docx`. Preserves paragraphs, table content, and heading hierarchies (`Heading 1`, `Heading 2`).
- **TXT (`.txt`)**: Extracted via multi-encoding fallback (`utf-8` -> `utf-8-sig` -> `latin-1`).

### Structural Recursive Chunking
Rather than using naive character-based or fixed-string slicing that divides words and breaks table rows, Clario employs `RecursiveStructureChunker`:
- **Target Chunk Size**: 500 tokens (~2,000 characters).
- **Chunk Overlap**: 75 tokens (~300 characters).
- **Separator Hierarchy**: `\n\n` (paragraphs) $\rightarrow$ `\n` (lines) $\rightarrow$ `. ` (sentences) $\rightarrow$ `; ` $\rightarrow$ `, ` $\rightarrow$ ` ` (words).
- **Lineage Preservation**: Tracks `page_number` (start page), `end_page` (for cross-page chunks), section headers, and sequential `chunk_index`.
- **Word Integrity**: Never splits across a word boundary. Oversized sections are subdivided recursively until fitting within token limits.

---

## 11. Retrieval Architecture

Clario implements a dual-stream hybrid retrieval architecture that merges dense semantic search with sparse lexical search:

```
                          ┌───────────────────────┐
                          │      User Query       │
                          └──────────┬────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  ▼                                     ▼
      ┌───────────────────────┐             ┌───────────────────────┐
      │   Semantic Stream     │             │     BM25 Stream       │
      │  BGE-small (384-d)    │             │  BM25Okapi In-Memory  │
      │  Qdrant Cosine Search │             │  Exact Token Matches  │
      └──────────┬────────────┘             └──────────┬────────────┘
                 │                                     │
                 └──────────────────┬──────────────────┘
                                    ▼
                      ┌───────────────────────────┐
                      │  Reciprocal Rank Fusion   │
                      │         (k = 60)          │
                      └─────────────┬─────────────┘
                                    ▼
                      ┌───────────────────────────┐
                      │  PostgreSQL Authorization │
                      │      Filtering Gate       │
                      └─────────────┬─────────────┘
                                    ▼
                      ┌───────────────────────────┐
                      │   Cross-Encoder Reranker  │
                      │   ms-marco-MiniLM-L-6-v2  │
                      └─────────────┬─────────────┘
                                    ▼
                      ┌───────────────────────────┐
                      │    Top-K Ranked Chunks    │
                      └───────────────────────────┘
```

### 1. Semantic Retrieval Stream
- Generates 384-dimensional dense vectors using `BAAI/bge-small-en-v1.5`.
- Executes cosine similarity search in Qdrant against the `clario_documents` collection.
- Retrieves candidates capable of bridging vocabulary gaps and understanding semantic intent.

### 2. Lexical Keyword Stream (BM25)
- Tokenizes query and canonical PostgreSQL chunks using an identifier-preserving regex: `r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*"`.
- Executes `BM25Okapi` scoring across all `READY` document chunks.
- Ensures high recall for alphanumeric error codes, product models, and exact policy numbers.

### 3. Reciprocal Rank Fusion (RRF)
Merges ranked lists from both retrievers using Reciprocal Rank Fusion with smoothing constant $k = 60$:

$$RRF(d) = \sum_{r \in \{\text{semantic}, \text{bm25}\}} \frac{1}{60 + \text{rank}_r(d)}$$

Where $\text{rank}_r(d)$ is the 1-based rank position of candidate $d$ in retriever $r$.
- **Tie-Breaking**: Deterministic multi-key sorting:
  1. Primary: RRF score descending.
  2. Secondary: Multi-retriever agreement count descending (chunks found by both streams rank higher).
  3. Tertiary: Chunk UUID string ascending for absolute reproducibility.

---

## 12. Cross-Encoder Reranking

First-stage hybrid retrieval retrieves an expanded candidate pool (typically $\max(\text{top\_k} \times 4, 20)$). The second-stage reranker applies deep neural cross-attention:

- **Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Method**: Evaluates `(query, chunk_content)` sentence pairs simultaneously through Transformer cross-attention layers, computing a relevance logit for each candidate.
- **Score Monotonicity & Transparency**: Preserves `initial_score` and `initial_rank` from first-stage retrieval while annotating `rerank_score`.
- **Fault-Tolerant Fallback**: If GPU/CPU cross-encoder inference encounters an operational error, the pipeline logs a warning and falls back gracefully to first-stage hybrid ordering without failing the user request.

---

## 13. Context Construction & Prompt Containment

The `ContextBuilder` formats retrieved candidate chunks into an optimized LLM prompt while enforcing security and budget constraints:

1. **Token Budget Allocation**:
   - Total context budget: 4,000 tokens (`LLM_CONTEXT_TOKEN_BUDGET`).
   - Safety margin: 250 tokens reserved for system instructions, formatting, and query overhead.
2. **Deduplication**: Normalizes candidate content (whitespace-insensitive) to prevent duplicate chunks from wasting token capacity.
3. **Prompt Injection Containment**:
   - Chunks are enclosed in structured XML tags: `<document index="1" id="..." filename="..." page="..." section="...">`.
   - Raw XML boundary breakouts (`</document>`, `</enterprise_context>`) inside chunk text are neutralized into bracketed tokens.
   - System prompt explicitly commands the model to treat all text within `<enterprise_context>` strictly as passive factual evidence, never instructions.
4. **Deterministic Source Tagging**: Assigns ascending 1-based source tags (`[Doc-1]`, `[Doc-2]`, etc.) corresponding directly to evidence blocks.
5. **Context Length Recovery**: If downstream LLM token limits are exceeded, Clario automatically drops the lowest-ranked chunk and retries generation once before returning an error.

---

## 14. LLM Generation & Provider Interface

Clario abstracts LLM generation through `BaseLLMProvider`, ensuring vendor neutrality:

- **OpenAI-Compatible Provider (`OpenAICompatibleProvider`)**:
  - Connects to OpenAI, Azure OpenAI, Ollama, or vLLM via `LLM_API_BASE_URL` and `LLM_API_KEY`.
  - Enforces deterministic output using fixed temperature `0.0`.
  - Configurable max output tokens (default: 1,024).
- **Deterministic Mock Provider (`MockLLMProvider`)**:
  - Offline fallback provider for continuous integration, local testing, and zero-cost reproduction.
  - Generates deterministic factual responses with inline citations directly grounded in supplied context.
- **Abstention Invariant**: If no candidate chunks match the query or context is empty, the model abstains immediately with:
  > *"I could not find sufficient information in the provided documentation to answer your question."*

---

## 15. Grounding & Faithfulness Verification

Clario includes a dedicated verification layer that evaluates whether generated answers are faithfully grounded in retrieved source context.

> [!NOTE]
> Verification does not certify absolute real-world truth. It evaluates whether generated claims are mathematically supported by the retrieved document chunks.

```
Synthesized Answer Text
         │
         ▼
┌──────────────────┐
│ Claim Extraction │  Splits text into atomic factual statements
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Pair Prioritize  │  Orders (claim, chunk) pairs:
│   & Global Cap   │  Explicit Citation > Jaccard Overlap > Rank
└────────┬─────────┘  Bounded by VERIFICATION_MAX_PAIRS (20)
         │
         ▼
┌──────────────────┐
│ NLI Inference    │  cross-encoder/nli-deberta-v3-small
│  (Batched Pairs) │  Predicts Entailment, Contradiction, Neutral
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Claim Labeling   │  SUPPORTED (Entailment >= 0.65)
│                  │  CONTRADICTED (Contradiction >= 0.55)
│                  │  INSUFFICIENT (Neutral / Below Threshold)
│                  │  UNVERIFIED (Truncated by Pair Cap)
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Answer Status    │  Strict Precedence:
│    Precedence    │  FAILED > INSUFFICIENT_EVID > NO_CLAIMS >
└──────────────────┘  CONTRADICTED > VERIFIED_FAITHFUL >
                      PARTIALLY_SUPPORTED > INCOMPLETE > UNSUPPORTED
```

### Claim Labels (Atomic Outcome per Claim)
- **`SUPPORTED`**: Evaluated against context chunks; entailment probability $\ge 0.65$, contradiction $< 0.55$, and all relevant candidate chunks evaluated.
- **`CONTRADICTED`**: Contradiction probability $\ge 0.55$ detected against any evaluated chunk, or conflicting claims present.
- **`INSUFFICIENT`**: Fully evaluated against all relevant chunks, but evidence is neutral or below the entailment threshold.
- **`UNVERIFIED`**: Candidate evaluation was truncated due to the global candidate pair cap (`VERIFICATION_MAX_PAIRS = 20`).

### Faithfulness Statuses (Strict Answer-Level Precedence)
1. **`VERIFICATION_FAILED`**: Operational timeout or exception in the NLI verifier.
2. **`INSUFFICIENT_EVIDENCE`**: Input context was empty or pipeline abstained.
3. **`NO_CLAIMS_FOUND`**: Context was present, but zero factual claims were extracted (e.g., conversational greetings).
4. **`CONTRADICTED`**: At least one atomic claim received a `CONTRADICTED` label.
5. **`VERIFIED_FAITHFUL`**: 100% of extracted claims ($N \ge 1$) are `SUPPORTED` and fully evaluated.
6. **`PARTIALLY_SUPPORTED`**: At least one claim is `SUPPORTED`, zero claims are `CONTRADICTED`, and remaining claims are `INSUFFICIENT` or `UNVERIFIED`.
7. **`INCOMPLETE_VERIFICATION`**: Zero claims are `SUPPORTED` or `CONTRADICTED`, but at least one claim is `UNVERIFIED` due to the pair cap.
8. **`UNSUPPORTED`**: 100% of extracted claims were fully evaluated and found `INSUFFICIENT`.

---

## 16. Citation Mapping & Sanitization

Every generated answer provides traceable source attribution back to retrieved document chunks:

1. **Inline Tag Extraction**: Scans generated text for `[Doc-1]`, `[Doc-2]`, etc.
2. **PostgreSQL Chunk Resolution**: Maps each tag back to its canonical chunk metadata:
   - `source_tag`: e.g., `"[Doc-1]"`
   - `chunk_id`: PostgreSQL UUID
   - `document_id`: Parent document UUID
   - `filename`: Original document filename
   - `page_number` & `end_page`: Original document page range
   - `section`: Heading or section title
   - `department`: Scoped department
   - `access_level`: Document classification level
   - `relevance_score`: First/second-stage retrieval score
3. **Hallucination Sanitization**: If the model references a tag not supplied in context (e.g., `[Doc-99]`), the tag is automatically stripped from the answer text and logged as an unmapped citation in telemetry.

---

## 17. Multi-Turn Conversations

Clario supports stateful, multi-turn conversational question answering:

- **Session Ownership Isolation**: Every conversation belongs to a specific `user_id`. Cross-user access is strictly forbidden (`HTTP 403 Forbidden`). Users cannot read, list, delete, or append messages to another user's sessions.
- **Conversation State Persistence**: PostgreSQL persists conversation sessions and individual message turns (`user`, `assistant`) alongside verification statuses.
- **Follow-Up Query Contextualization**: When a user asks an elliptical follow-up question (e.g., *"What about remote employees?"* or *"Can they use it on weekends?"*), `GenerationService.contextualize_query()` reformulates the retrieval query using key terms from preceding user turns before executing hybrid search.
- **Prompt History Packaging**: Injects up to 6 prior dialogue turns into `<conversation_history>` within the LLM prompt.

---

## 18. Enterprise Audit Logging

Clario records security-relevant operations in the `audit_logs` table:

- **Logged Actions**: `register`, `login`, `upload`, `process`, `delete`, `search`, `query`.
- **Captured Metadata**: `user_id`, `action`, `resource_type`, `resource_id`, `details` (JSONB), and `created_at`.
- **Sensitive Key Sanitization**: `AuditService` recursively scrubs sensitive keys from log details before database write:
  - Redacted keys: `password`, `token`, `access_token`, `refresh_token`, `jwt`, `secret`, `api_key`, `authorization`, `key`.
- **Role-Gated Access**: The audit log API endpoint (`GET /api/v1/audit-logs`) is restricted to `admin` and `analyst` roles. Regular users are barred (`HTTP 403 Forbidden`).

---

## 19. API Reference

All endpoints are served under `/api/v1` except the root health and welcome routes:

### System & Health
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Root system health check (PostgreSQL and Qdrant status) | No |
| `GET` | `/api/v1/health` | API v1 health check endpoint | No |
| `GET` | `/` | Service name and documentation URLs | No |

### Authentication
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register new user account and receive JWT token | No |
| `POST` | `/api/v1/auth/login` | Authenticate with email/password and receive JWT token | No |
| `GET` | `/api/v1/auth/me` | Retrieve current authenticated user profile and roles | Bearer Token |

### Document Management
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/documents/upload` | Upload original PDF, DOCX, or TXT file with metadata | Optional / Scoped |
| `POST` | `/api/v1/documents/{id}/process` | Trigger async parsing, chunking, and vector indexing | Authorized User |
| `GET` | `/api/v1/documents` | List paginated documents with department and status filters | Optional / Filtered |
| `GET` | `/api/v1/documents/{id}` | Get document metadata, processing status, and chunk count | Authorized User |
| `DELETE`| `/api/v1/documents/{id}` | Delete document, chunks, Qdrant vectors, BM25, and file | Admin or Uploader |

### Search & Knowledge Retrieval
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/search` | Standalone hybrid, semantic, or BM25 search with rerank toggle | Optional / Filtered |
| `POST` | `/api/v1/query` | End-to-end RAG question answering with citations & verification| Optional / Filtered |

### Multi-Turn Conversations
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/conversations` | Create new multi-turn conversation session | Bearer Token |
| `GET` | `/api/v1/conversations` | List conversations owned by authenticated user | Bearer Token |
| `GET` | `/api/v1/conversations/{id}` | Get full message history for owned conversation | Bearer Token |
| `DELETE`| `/api/v1/conversations/{id}` | Delete owned conversation session | Bearer Token |
| `POST` | `/api/v1/conversations/{id}/messages` | Post user message, run RAG Q&A, and save assistant reply | Bearer Token |

### Governance & Audit
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/audit-logs` | List security audit records (paginated, action/resource filters) | Admin or Analyst |

---

## 20. Frontend Interface

The Clario frontend is built with React 19 and Vite using a custom enterprise design system.

### Implemented UI Capabilities
- **Authentication Screens**: Login and registration with department selection and error handling.
- **Enterprise Application Layout (`AppLayout`)**: Header with live environment badge (`DEVELOPMENT` / `PRODUCTION`), user avatar initials, display name, department badge, and secure sign-out.
- **Documents Workspace (`Documents`)**:
  - Paginated document table displaying title, filename, department, access level, byte size, created date, and color-coded status badges (`READY`, `PROCESSING`, `UPLOADED`, `FAILED`).
  - Search and filter bar supporting department, status, and access level filtering.
  - Multipart upload modal supporting file drag-and-drop, title, department, and access level assignment.
  - Document detail drawer showing comprehensive file metadata, asynchronous processing trigger, chunk count, and deletion.
  - Chunk viewer displaying parsed chunks, token lengths, page numbers, and section headers.
- **Identity & Health Dashboard (`Dashboard`)**: Real-time backend and vector database connectivity check, active user credentials, assigned roles, and session token inspection.

### Planned UI Views (Roadmap)
- **Knowledge Chat View**: Dedicated full-screen conversational interface with inline citation expanding drawers and live verification badges (indicated as *Knowledge Chat (Next)* in navigation).
- **Semantic Search View**: Interactive exploratory search view with rank comparison and similarity score distribution.
- **Audit Log Explorer**: Dedicated administrative data table for viewing, searching, and filtering security audit events.

---

## 21. Evaluation Strategy & Benchmark Suite

Clario includes an Information Retrieval evaluation benchmark built directly into the test suite (`backend/tests/test_hybrid_retrieval.py` and `test_reranking.py`).

### Information Retrieval Evaluation Framework
Evaluates retrieval quality across six distinct query archetypes:

1. **Exact Code Identifier** (e.g., `"ERR-DB-504"`): Tests exact token match capability on hyphenated error strings.
2. **Exact Policy Identifier** (e.g., `"POL-HR-2026-A"`): Tests policy code retrieval.
3. **Vocabulary Mismatch / Synonym** (e.g., `"paid sick leave and health days for employee doctor visits"`): Tests semantic retrieval across differing vocabularies.
4. **Multi-Relevant Target** (e.g., `"remote corporate VPN access requirements and credentials"`): Tests retrieval where multiple relevant chunks exist across documents.
5. **Conceptual Semantic Paraphrase** (e.g., `"How many days off can staff take for annual summer holidays?"`): Tests high-level paraphrase matching.
6. **Out-of-Domain Zero-Match** (e.g., `"quantum computing entanglement teleportation protocol"`): Tests safe handling of queries with zero relevant documents.

### IR Metrics Formulation
- **Precision@K**: $\frac{|\text{Relevant Chunks in Top-K}|}{K}$ (uses fixed cutoff $K$ as denominator).
- **Recall@K**: $\frac{|\text{Relevant Chunks in Top-K}|}{|\text{Total Relevant Chunks}|}$.
- **Mean Reciprocal Rank (MRR)**: $\frac{1}{\text{Rank of First Relevant Chunk}}$ (0.0 if no relevant chunk in top-K).
- **Zero-Relevant Query Convention**: For out-of-domain queries with no relevant chunks, Precision, Recall, and MRR are defined as 0.0 and included in macro averages.

### Verification Benchmark (8 NLI Archetypes)
The verification engine is validated against eight ground-truth archetypes in `test_nli_verifier.py`:
1. Exact entailment $\rightarrow$ `VERIFIED_FAITHFUL`
2. Paraphrased entailment $\rightarrow$ `VERIFIED_FAITHFUL`
3. Direct factual contradiction $\rightarrow$ `CONTRADICTED`
4. Numeric or insufficient evidence $\rightarrow$ `UNSUPPORTED`
5. Unmapped citation tag $\rightarrow$ Tag flagged and stripped
6. Conflicting evidence in context $\rightarrow$ `CONTRADICTED`
7. Zero factual claims in answer $\rightarrow$ `NO_CLAIMS_FOUND`
8. Empty context abstention $\rightarrow$ `INSUFFICIENT_EVIDENCE`

---

## 22. Test Suite & Verification

The repository contains 23 comprehensive automated backend test modules in `backend/tests/`:

```bash
backend/tests/
├── test_health.py                  # Root /health, /api/v1/health, and welcome endpoints
├── test_database.py                # PostgreSQL connectivity, models, FKs, Qdrant collection
├── test_storage_backends.py        # Local file storage, path traversal protection, S3 mocks
├── test_parsers.py                 # PDF, DOCX, TXT parsers, Unicode handling, corrupt files
├── test_chunking.py                # Recursive chunking, headings, overlap, token counters
├── test_embeddings.py              # BGE-small 384-d vectors, batching, Qdrant upserts
├── test_retrieval.py               # Semantic search, PostgreSQL hydration, filters, pagination
├── test_hybrid_retrieval.py        # BM25, RRF formula, comparative evaluation benchmark
├── test_reranking.py               # Cross-Encoder lazy loading, logits, fallback, benchmark
├── test_context_builder.py         # Token budgeting, XML containment, prompt injection defense
├── test_llm_provider.py            # OpenAI provider, 401 fail-fast, 429 retries, mock provider
├── test_generation.py              # End-to-end Q&A, citation extraction, abstention on empty
├── test_claim_extractor.py         # Claim segmentation, citation tag parsing, clause splits
├── test_nli_verifier.py            # 8 NLI archetypes, entailment/contradiction thresholds
├── test_verification_integration.py# Pair cap truncation, precedence rules, verify toggle
├── test_conversations.py           # Session CRUD, user isolation, message persistence
├── test_conversation_followup.py   # Follow-up query contextualization & history inclusion
├── test_auth_and_rbac.py           # User registration, login, JWT validation, role checks
├── test_security_authorization.py  # Server-side hydration filtering, unauthenticated checks
├── test_documents.py               # Upload validation, magic bytes, delete cascade
├── test_document_endpoints.py      # REST endpoints for documents, filters, details
├── test_background_processing.py   # Asynchronous document processing pipeline
└── test_audit_service.py           # Audit logging, sensitive key redaction, role gating
```

---

## 23. Installation & Local Setup

### Prerequisites
- **Python**: 3.11+ (tested on Python 3.12)
- **Node.js**: 18+ (tested on Node 20+)
- **Docker & Docker Compose**: Docker Engine 24+ and Docker Compose v2+
- **Git**

### 1. Clone Repository & Setup Environment
```bash
git clone https://github.com/Amar-7778/clario.git
cd clario

# Copy example environment configuration
cp .env.example .env
```

### 2. Start Storage Infrastructure (PostgreSQL & Qdrant)
Run Docker Compose from the project root to start PostgreSQL 16 and Qdrant 1.10:
```bash
docker compose up -d
```

Verify that both containers are running and healthy:
```bash
docker compose ps
```
- PostgreSQL: `localhost:5432`
- Qdrant HTTP: `http://localhost:6333`
- Qdrant gRPC: `localhost:6334`

### 3. Setup & Start Backend (FastAPI)
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate       # On Windows: .venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI server with live reload
uvicorn app.main:app --reload --port 8000
```
- Backend API: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### 4. Setup & Start Frontend (React 19 + Vite)
```bash
# Open a new terminal window
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
- Open `http://localhost:5173` to access the Clario enterprise console.

---

## 24. Environment Configuration

All configuration is managed through Pydantic Settings in `backend/app/core/config.py` and sourced from `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`). |
| `PORT` | `8000` | FastAPI server listening port. |
| `HOST` | `0.0.0.0` | FastAPI server listening host. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed CORS origins (comma-separated or JSON list). |
| `DATABASE_URL` | `postgresql+psycopg://clario_user:clario_password@localhost:5432/clario_db` | Relational PostgreSQL connection string. |
| `POSTGRES_USER` | `clario_user` | PostgreSQL database user. |
| `POSTGRES_PASSWORD` | `clario_password` | PostgreSQL database password. |
| `POSTGRES_DB` | `clario_db` | PostgreSQL database name. |
| `POSTGRES_PORT` | `5432` | PostgreSQL exposed host port. |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector database URL. |
| `QDRANT_COLLECTION_NAME` | `clario_documents` | Target collection name in Qdrant. |
| `EMBEDDING_MODEL_NAME` | `BAAI/bge-small-en-v1.5` | SentenceTransformers embedding model. |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimensionality. |
| `RERANKING_ENABLED` | `True` | Whether Cross-Encoder reranking is enabled by default. |
| `RERANKING_MODEL_NAME` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Cross-Encoder model name for second-stage ranking. |
| `RRF_K` | `60` | Reciprocal Rank Fusion smoothing constant. |
| `STORAGE_BACKEND` | `local` | Document file storage backend (`local`, `s3`, `r2`). |
| `STORAGE_DIR` | `storage` | Local directory for uploaded files. |
| `MAX_UPLOAD_SIZE_BYTES` | `52428800` | Maximum file upload size in bytes (50 MB). |
| `CHUNK_SIZE` | `500` | Target chunk size in tokens (~2,000 chars). |
| `CHUNK_OVERLAP` | `75` | Target chunk overlap in tokens (~300 chars). |
| `JWT_SECRET` | `default-jwt-secret-key-change-in-production` | Secret key for HMAC-SHA256 JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24 hours) | Token expiration duration in minutes. |
| `LLM_PROVIDER` | `mock` | Active LLM provider (`mock`, `openai`, `azure`, `ollama`, `vllm`). |
| `LLM_MODEL_NAME` | `gpt-4o-mini` | Generation model name. |
| `LLM_API_KEY` | `None` | API key for external LLM provider. |
| `LLM_TEMPERATURE` | `0.0` | Generation temperature (fixed 0.0 for enterprise facts). |
| `VERIFICATION_ENABLED` | `False` | Whether NLI grounding verification runs by default. |
| `VERIFICATION_MODEL_NAME` | `cross-encoder/nli-deberta-v3-small` | Cross-Encoder NLI model for verification. |
| `VERIFICATION_MAX_PAIRS` | `20` | Maximum candidate pairs evaluated per query. |
| `VERIFICATION_ENTAILMENT_THRESHOLD` | `0.65` | NLI probability threshold for entailment. |
| `VERIFICATION_CONTRADICTION_THRESHOLD` | `0.55` | NLI probability threshold for contradiction. |

---

## 25. Security & Governance Notes

1. **Server-Side Authorization Invariant**: Authorization filtering is applied at the database hydration layer before ranking, reranking, and context construction. Unauthorized records never enter the prompt.
2. **Untrusted Data Containment**: Uploaded files and retrieved document text are treated as untrusted data. Special XML tags are neutralized to prevent prompt injection breakouts.
3. **Sensitive Audit Scrubbing**: All audit events pass through recursive key scrubbing. Passwords, bearer tokens, API keys, and authorization headers are never written to audit tables.
4. **Session Isolation**: Conversation sessions enforce strict ownership checks. An authenticated user attempting to read or post messages to another user's session receives an immediate `HTTP 403 Forbidden`.
5. **Path Traversal Defenses**: Document upload and storage services validate file headers and sanitize filenames, rejecting path traversal attempts (`../`) and unauthorized extensions.

---

## 26. Known Limitations

1. **In-Memory BM25 Index**: The BM25 index currently resides in application process memory. While it rebuilds deterministically from PostgreSQL on startup and invalidation, multi-worker horizontal scaling requires shared caching (e.g., Redis) or Elasticsearch/OpenSearch.
2. **CPU NLI Verification Latency**: When running `cross-encoder/nli-deberta-v3-small` on CPU without GPU acceleration, verifying 20 candidate pairs adds 300ms–800ms to query latency. It is disabled by default (`VERIFICATION_ENABLED=False`) and can be enabled per-request via `verify=true`.
3. **Synchronous LLM Generation**: The `/api/v1/query` endpoint returns a completed JSON payload. Server-Sent Events (SSE) or WebSocket streaming is planned for real-time token streaming.
4. **OCR Not Included**: PDF parsing relies on native text extraction via `pypdf`. Scanned image-only PDFs without an embedded OCR text layer will return empty extracted text and fail validation.

---

## 27. Future Roadmap

- [ ] **Streaming Responses (SSE)**: Implement Server-Sent Events for progressive streaming of generated tokens and real-time verification indicators.
- [ ] **Dedicated Knowledge Chat UI**: Complete the conversational chat interface in the React frontend with multi-turn sidebar sessions and expandable citation sidecars.
- [ ] **Audit Log Explorer UI**: Implement an administrative audit ledger table in the frontend with date-range filters and CSV export.
- [ ] **OCR Ingestion Pipeline**: Integrate Tesseract or PyMuPDF OCR for scanned image-based PDF documents.
- [ ] **Distributed BM25 Indexing**: Offload lexical indexing to a shared search cluster (e.g., Qdrant sparse vectors or OpenSearch) for multi-node deployments.
- [ ] **Asynchronous Webhook Notifications**: Webhook alerts when long document processing jobs transition to `READY` or `FAILED`.

---

## 28. License

Clario is distributed under the [MIT License](LICENSE).
