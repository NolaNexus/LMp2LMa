# ADR-003: Data Storage - PostgreSQL + pgvector for Embeddings

**Status**: Accepted
**Date**: 2026-11-01
**Deciders**: ML Architect Team
**Technical Story**: Choose data storage solution for tickets, embeddings, and analytics

## Context

Data requirements:
- Ticket metadata (title, description, customer, priority, status, timestamps)
- Conversation history (messages, LLM responses, human interventions)
- Embeddings for semantic search and classification (1536-dim for OpenAI, 1024/4096 for others)
- Analytics events (classification accuracy, response quality, escalation rates)
- Audit logs for compliance
- ~10M tickets/year, ~100M messages/year

Requirements:
- ACID transactions for ticket state changes
- Vector similarity search (k-NN) for semantic retrieval
- Horizontal scaling for embeddings
- Cost-effective for embedding storage
- Familiar tooling (SQL)
- Backup/restore simplicity

## Decision

**PostgreSQL with pgvector extension** for primary storage:

- **Tickets & Metadata**: Standard relational tables with JSONB for flexible fields
- **Embeddings**: pgvector HNSW index for approximate k-NN search
- **Conversations**: Partitioned table by date for performance
- **Analytics**: Materialized views refreshed hourly
- **Audit**: Append-only table with triggers

## Consequences

**Positive**:
- Single database for all data (simplifies ops)
- pgvector performance competitive with dedicated vector DBs at our scale
- SQL familiarity across team
- ACID guarantees for ticket operations
- pgvector supports HNSW and IVFFlat indexes
- Backup/restore with standard pg_dump

**Negative**:
- Vector search performance degrades >100M vectors (mitigation: partitioning)
- HNSW index build time at scale
- Less advanced vector features (filtering, hybrid search) vs Pinecone/Weaviate

## Alternatives Considered

1. **Pinecone/Weaviate/Qdrant**: Better vector features but separate system, cost, complexity
2. **Elasticsearch**: Good hybrid search but heavier ops, licensing changes
3. **Redis + Vector**: Fast but not durable for primary storage
4. **ClickHouse + Vector**: Great analytics but complex for transactional workload

## Implementation Notes

- `capstone/infrastructure/database/schema.sql` - DDL with pgvector
- `capstone/infrastructure/database/migrations/` - Alembic migrations
- Connection pooling: PgBouncer
- Read replicas for analytics queries
- Embedding dimension per provider stored in metadata column
- HNSW index: `CREATE INDEX ON embeddings USING hnsw (vector vector_cosine_ops) WITH (m=16, ef_construction=64)`