# Investment Intelligence Lab

A high-performance RAG environment for investment research, using **RAGFlow** for archival data, **TrustGraph** for current relationship mapping, and **Kestra** for Python-powered tool orchestration.

## The 3 Pillars

1.  **Pilot (Kestra)**: Orchestrates workflows and calls tools (SEC downloaders, news scrapers).
2.  **Library (RAGFlow)**: Deep document સમજ (understanding) for books and fundamental reports.
3.  **Garden (TrustGraph)**: Interactive 3D visualization and pruning of current market relationships.

## Quick Start

### 1. Launch Infrastucture
```bash
docker compose up -d
```

### 2. Verify Dashboards
- **Kestra**: [http://localhost:8081](http://localhost:8081)
- **TrustGraph**: [http://localhost:8888](http://localhost:8888)
- **Neo4j**: [http://localhost:7474](http://localhost:7474)

### 3. Configure API Keys
1. Copy `.env.example` to `.env`.
2. Add your **OpenRouter**, **OpenAI**, or **Claude** keys.
3. RAGFlow and TrustGraph will use these for high-performance reasoning.

## Project Structure
- `data/`: Persistent storage for all databases.
- `flows/`: Kestra workflow definitions.
- `ragflow/`: Local RAGFlow instance (Submodule/Folder).
- `scripts/`: Custom Python tools for investment analysis.
