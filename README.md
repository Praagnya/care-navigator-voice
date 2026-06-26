# Care Navigator Voice

A conversational health-navigation agent that helps users find appropriate care facilities using real provider data. Not a diagnosis tool.

## What it does

- Multi-turn conversation to gather symptoms, location, and urgency
- Detects emergencies on every turn and escalates immediately
- Looks up real facilities from CMS public provider data
- Only recommends providers that exist in the database — no hallucinated results
- Voice layer sits on top of the text core

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Orchestration | LangGraph |
| LLM | OpenAI GPT-4o |
| Database | PostgreSQL + SQLAlchemy (async) |
| Migrations | Alembic |
| Data pipeline | Pandas + Pandera |
| Observability | Structlog + Langfuse |
| Package manager | uv |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |
| Cloud | AWS ECS Fargate + RDS + S3 |

## Local setup

```bash
# 1. Copy environment config
cp .env.example .env
# Fill in OPENAI_API_KEY and other values

# 2. Install dependencies
uv sync --all-extras

# 3. Start Postgres
docker compose up postgres -d

# 4. Run migrations
uv run alembic upgrade head

# 5. Start the API
uv run uvicorn app.main:app --reload
```

## Project structure

```
app/                    # FastAPI application
  config.py             # Typed settings via pydantic-settings
  main.py               # API entrypoint, /health, /ready
  schemas.py            # Pydantic request/response models
  core/                 # LangGraph agent and state
  safety/               # Emergency detection, guardrails
  retrieval/            # Provider search and grounding
  llm/                  # LLM client and prompt management
  observability/        # Structured logging

data_pipeline/          # CMS data ingestion pipeline
  sources/              # Dataset downloaders (CMS, NPPES)
  validation/           # Hard and soft validation rules
  transforms/           # Normalization and deduplication
  db/                   # SQLAlchemy models and Alembic migrations
  ingest.py             # Pipeline orchestrator

tests/                  # Unit and integration tests
evaluation/             # Golden eval cases and eval runner
prompts/                # Versioned prompt files
.github/workflows/      # CI/CD pipelines
```

## Data pipeline

The pipeline ingests CMS Hospital General Information data on a schedule:

```
Download → Validate → Normalize → Deduplicate → Load into PostgreSQL
```

Every run is tracked with source URL, row counts, rejection reasons, and dataset version — enabling full data lineage.

## Safety

Emergency detection runs on every user turn before any other logic. The system follows a deterministic escalation policy and does not rely solely on LLM judgment for safety-critical decisions.

## License

MIT
