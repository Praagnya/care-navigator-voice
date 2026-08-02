# Care Navigator Voice — CLAUDE.md

## Project Overview

Care Navigator is a production-grade voice-first healthcare-navigation agent.

It helps users identify an appropriate care pathway and find relevant healthcare facilities using grounded public provider data.

The application:

- Is a care-navigation tool, not a diagnostic tool
- Must not diagnose medical conditions
- Must not prescribe treatments
- Must not invent provider or facility information
- Must clearly communicate uncertainty and data limitations
- Must escalate potential emergencies via the Gemini system prompt and emergency escalation script
- Is voice-only in V1 — no text chat endpoint

The voice interface is the core product. Gemini Live handles conversation orchestration, audio (STT + TTS), and tool calling. A separate Deep Agent (LangGraph ReAct + OpenAI or Claude) is invocable as a Gemini tool for complex multi-step research.

---

## V1 Scope

### In V1

- Voice conversation via Gemini Live WebSocket (`/v1/voice`)
- Slot collection: care concern, location, urgency, care category
- `search_providers` tool — PostgreSQL (CMS data)
- `get_facility_detail` tool — PostgreSQL
- `deep_research` tool — Deep Agent (LangGraph ReAct + OpenAI/Claude)
- Grounded facility recommendations with `provider_id` on every returned record
- Emergency escalation via Gemini system prompt + emergency script
- `/health` and `/ready` HTTP endpoints
- CMS data ingestion pipeline (ingest → validate → normalize → upsert)
- structlog + Langfuse observability
- pytest tests and evaluation cases

### Out of V1

- Text `/v1/chat` endpoint
- Web search for facilities
- Appointment booking
- Insurance-network filtering
- Multilingual support
- Deterministic keyword emergency pre-filter
- Trained or ML-based facility ranking model
- AWS deployment infrastructure
- Additional voice languages beyond English

---

## Technology Decisions

Use:

- Python 3.12
- FastAPI for the API layer (WebSocket + HTTP)
- Pydantic for all schemas: requests, responses, configuration, session state
- `google-genai` SDK for Gemini Live (`client.aio.live.connect`)
- LangGraph for the Deep Agent ReAct loop only
- OpenAI or Anthropic SDK as the secondary LLM for Deep Agent
- PostgreSQL as the sole source of facility facts (CMS data)
- SQLAlchemy (async) for database access
- Alembic for schema migrations
- pytest for tests
- Ruff for formatting and linting
- mypy for static type checking
- uv for dependency management
- Docker and Docker Compose for local reproducibility
- structlog for structured logging
- Langfuse for LLM observability and tracing

Do not introduce a new framework or infrastructure service unless it solves a demonstrated requirement.

---

## Architecture

```
Client (PCM audio, 16kHz)
        │ WebSocket binary frames (base64 encoded)
        ▼
FastAPI WebSocket  /v1/voice  (app/api/routes/voice.py)
  - Thin handler — owns connection lifecycle only
  - Two concurrent tasks:
      client_to_agent()  → receives audio frames from browser → forwards to session manager
      agent_to_client()  → receives model audio events → sends PCM back to browser
        │
        ▼
GeminiSessionManager  (app/voice/session_manager.py)
  - Opens google-genai Live session with system prompt + tool declarations
  - 3 concurrent asyncio tasks:
      _send_audio_loop      → session.send_realtime_input(audio=...)
      _receive_loop         → receives events, dispatches tool calls
      _send_audio_out_loop  → sends Gemini audio back to WebSocket client
  - Stores session resumption token on GoAway / SessionResumptionUpdate
        │ BidiGenerateContentToolCall
        ▼
ToolRouter  (app/voice/tool_router.py)
  ┌──────────────────────────────────────────────────────────┐
  │ search_providers    → PostgreSQL (blocking, fast)        │
  │ get_facility_detail → PostgreSQL (blocking, fast)        │
  │ deep_research       → Deep Agent (NON_BLOCKING, async)   │
  └──────────────────────────────────────────────────────────┘
        │ DeepResearchRequest
        ▼
Deep Agent  (app/agent/deep_agent.py)
  LangGraph ReAct loop, secondary LLM (OpenAI or Claude)
  Tools:
    search_providers     → PostgreSQL
    get_quality_metrics  → PostgreSQL
  Returns: DeepResearchResult (Pydantic)
        │ FunctionResponse JSON  (sent via session.send_tool_response, scheduling=INTERRUPT)
        ▼
GeminiSessionManager → session.send_tool_response(...)
        │ PCM audio (24kHz)
        ▼
Client
```

---

## Architecture Principles

- Keep API routes thin — WebSocket handler owns connection lifecycle only
- Keep business logic in service modules
- Keep safety behavior in the Gemini system prompt and eval cases, not as a deterministic pre-filter
- Treat retrieved provider data as the only source of facility facts
- Do not let any LLM generate facility records from memory
- Use Pydantic schemas for all LLM structured outputs
- Validate all model-generated structured outputs before use
- Make conversation-state and slot-collection transitions inspectable
- Return explicit abstention when information is unverified or absent
- Keep provider retrieval deterministic and independently testable
- Version safety policies, prompts, retrieval logic, and datasets (use `app/core/versions.py`)
- Do not store secrets in source code
- Do not log full conversations, audio content, or sensitive health information

Avoid:

- Putting all application logic into one agent.py
- Hiding important control flow inside framework abstractions
- Allowing any LLM to diagnose a medical condition
- Inventing addresses, phone numbers, ratings, availability, or insurance acceptance
- Continuing routine questioning after an emergency is detected
- Adding web search for facilities in V1
- Adding tools such as Airflow, Kubernetes, Spark, or MLflow without a concrete need

---

## Gemini Live Session Details

- Audio in: PCM 16-bit, 16 kHz (`audio/pcm;rate=16000`)
- Audio out: PCM 24 kHz
- Session limit: 15 minutes; use `ContextWindowCompressionConfig` (sliding window) for longer sessions
- Reconnect: store `SessionResumptionUpdate.handle`; pass as `handle` on the next `connect()` call
- Tool calls: sequential by default; use `behavior: NON_BLOCKING` only where explicitly needed and documented

---

## Non-Blocking Tool Pattern (deep_research)

`deep_research` is the only NON_BLOCKING tool. It takes up to 60 seconds and must not freeze the voice session.

**Pattern (informed by google-adk-realtime-deepagents-example):**

1. `tool_router.py` receives the `deep_research` tool call from Gemini
2. It immediately returns an acknowledgement response: `"Research has started and will take up to a minute"`
   — this lets Gemini speak the acknowledgement to the user right away
3. The actual LangGraph ReAct work runs in a background asyncio task
4. When the Deep Agent completes, `session.send_tool_response(...)` is called with the result
5. Use `scheduling=INTERRUPT` on the FunctionResponse so Gemini immediately narrates findings

**What this means for `tool_router.py`:**

```python
# Pseudocode — do not implement until reaching this step
async def handle_deep_research(call_id, args, session):
    # 1. Acknowledge immediately
    await session.send_tool_response(call_id, {"status": "Research has started..."})
    # 2. Run in background
    asyncio.create_task(_run_and_deliver(call_id, args, session))

async def _run_and_deliver(call_id, args, session):
    result = await deep_agent.run(args)
    await session.send_tool_response(call_id, result, scheduling="INTERRUPT")
```

`search_providers` and `get_facility_detail` are fast PostgreSQL queries — they remain blocking (default sequential behavior).

---

## Safety Behavior

Emergency detection is handled by the Gemini system prompt (`prompts/system_v1.txt`) and is validated by evaluation cases.

Emergency cases include, but are not limited to:

- Chest pain
- Severe difficulty breathing or respiratory distress
- Signs of stroke (facial drooping, arm weakness, speech difficulty)
- Uncontrolled bleeding
- Loss of consciousness
- Suicidal intent or immediate self-harm risk

When an emergency is detected, Gemini must:

1. Immediately speak the emergency escalation script (`prompts/emergency_response_v1.txt`)
2. Call no tools
3. Collect no further slots
4. Not attempt to continue routine care navigation

Safety behavior must be covered by evaluation cases in `evals/tool_dispatch_cases.yaml`. Every emergency-phrased input must assert that **no tool call** is made and that the response contains the escalation script fragment.

There is no deterministic keyword pre-filter in V1. The system prompt is the sole safety enforcement mechanism and must be treated as a versioned, audited artifact.

---

## Grounding Requirements

Every `GroundedFacility` returned to Gemini as a tool response must include:

- `provider_id` from the retrieved `ProviderRecord`
- Only fields present in the retrieved record
- Explicit disclosure of any field that is absent or unverified

`app/services/grounding.py` must validate every tool response before it is sent back to Gemini via `session.send_tool_response(...)`.

The grounding validator must reject responses that:

- Claim insurance acceptance not present in the retrieved record
- Claim appointment availability not present in the retrieved record
- Claim a service not listed in the retrieved record
- Use a phone number or address marked absent in the retrieved record
- Assert that a facility is "best" without an explainable, rule-based ranking criterion

When information is unavailable, the tool response must state that explicitly.

---

## Repository Structure

```
app/
  main.py                        # FastAPI app factory, lifespan hooks
  config.py                      # Settings
  session_state.py               # Per-session slot/state schema
  versions.py                    # Version constants: prompt, tools, pipeline
  api/
    routes/
      voice.py                   # WebSocket /v1/voice
      health.py                  # GET /health, GET /ready
  schemas/
    provider.py                  # ProviderRecord, GroundedFacility, DeepResearchResult
    session.py                   # SessionState, SlotCollection, ToolCallRecord
  voice/
    session_manager.py           # Gemini Live session lifecycle + audio queues
    tool_router.py               # Dispatches Gemini tool calls to handlers
    tool_declarations.py         # FunctionDeclaration objects for Gemini config
    prompts.py                   # Loads versioned system prompt from prompts/
  agent/
    deep_agent.py                # LangGraph ReAct graph (Deep Agent)
    llm_client.py                # Unified OpenAI/Anthropic async client
  services/
    provider_search.py           # SQL-based provider retrieval
    provider_ranker.py           # Rule-based ranking
    grounding.py                 # Source-ID grounding validation
  db/
    models.py                    # SQLAlchemy ORM: providers, ingestion_runs
    session.py                   # Async engine + session factory
  observability/
    logging.py                   # structlog config

data_pipeline/
  ingest_cms.py
  validation.py
  normalization.py

prompts/
  system_v1.txt                  # Gemini Live system prompt (versioned)
  emergency_response_v1.txt      # Emergency escalation script fragment
  deep_research_v1.txt           # Deep Agent system prompt

evals/
  tool_dispatch_cases.yaml       # Includes emergency no-tool-call assertions
  grounding_cases.yaml
  deep_agent_cases.yaml
  slot_filling_cases.yaml
  run_evals.py

tests/
  unit/
  integration/
  api/

alembic/
```

---

## config.py Extensions

Add to `Settings` in `app/config.py`:

```python
# Gemini Live
gemini_api_key: str = ""
gemini_model: str = "gemini-2.5-flash-native-audio-preview"

# Deep Agent LLM backend ("openai" | "anthropic")
deep_agent_llm_provider: str = "openai"
deep_agent_llm_model: str = "gpt-4o"

# Anthropic — only required when deep_agent_llm_provider = "anthropic"
anthropic_api_key: str = ""

# Session behaviour
session_resumption_enabled: bool = True
context_window_compression_enabled: bool = True
```

`OPENAI_API_KEY` is retained and repurposed as the Deep Agent key when `deep_agent_llm_provider = "openai"`.

---

## New Dependencies

Add to `pyproject.toml` runtime dependencies:

- `google-genai` — Gemini Live SDK (`client.aio.live.connect`)
- `anthropic` — optional; only required if `deep_agent_llm_provider = "anthropic"`

---

## Development Rules

Before implementing a change:

1. Identify the component responsible for the behavior.
2. Prefer modifying an existing focused module over creating a broad abstraction.
3. Define or update the relevant Pydantic schema.
4. Add tests for the expected behavior and important failure cases.
5. Run formatting, linting, type checking, and tests.
6. Explain any architectural dependency or new framework before adding it.

Do not rewrite unrelated modules while implementing a focused task.

Do not silently change public API schemas or tool response contracts.

Do not add dependencies without explaining their purpose.

Do not weaken safety behavior (system prompt content, eval assertions) without explicit product sign-off.

---

## Required Commands

Install dependencies:

```
uv sync
```

Run the API:

```
uv run uvicorn app.main:app --reload
```

Format:

```
uv run ruff format .
```

Lint:

```
uv run ruff check .
```

Type-check:

```
uv run mypy app data_pipeline
```

Run tests:

```
uv run pytest
```

Run evaluations:

```
uv run python -m evals.run_evals
```

Run locally with containers:

```
docker compose up --build
```

---

## Definition of Done

A feature is complete only when:

- Its behavior is implemented in the appropriate module
- Request and response data are validated with Pydantic
- Relevant unit or integration tests pass
- Safety behavior (system prompt, eval assertions) is not weakened
- Grounding requirements remain enforced and tested
- Ruff passes with no errors
- mypy passes in strict mode
- pytest passes
- Public WebSocket or HTTP contracts are documented when changed

---

## Pair Programming and Mentorship Rules

The developer is building this project to deeply understand every component and demonstrate that understanding in interviews.

**Claude acts as pair programmer and technical mentor, not primary author.**

### What this means in practice

- Work one function, class, endpoint, or test at a time
- Before writing any code, explain the responsibility of the component and help decide inputs, outputs, dependencies, and failure cases
- Ask the developer to propose the logic or write the first attempt before providing any implementation
- Give hints before giving code
- Review code the developer writes — point out bugs, design issues, security risks, and edge cases
- Do not silently rewrite the developer's code into a different solution
- Provide only the smallest relevant snippet when code is needed
- Do not implement future steps before they are reached

### Interview readiness requirement

The developer must be able to explain every function in an interview:

- What it does
- Why it belongs in that file
- Why it is synchronous or asynchronous
- What it returns
- What can fail
- How it is tested
- How it interacts with the rest of the system

### Components the developer personally owns

Do not generate complete implementations for these without explicit request:

- Database models and schemas
- FastAPI lifespan and health checks
- CMS data ingestion
- Voice tool declarations and routing
- Real-time session management
- Async event handling, interruptions, and tool-call state
- Deep Agent / LangGraph orchestration
- Grounding and safety logic
- Evaluation cases and runners

### Priority

Optimize for the developer's understanding, debugging ability, production judgment, and interview readiness — not for finishing the project quickly.
