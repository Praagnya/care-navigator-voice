CLAUDE.md

Project Overview

Care Navigator is a production-oriented conversational healthcare-navigation application.

It helps users identify an appropriate care pathway and find relevant healthcare facilities using grounded public provider data.

The application:

* Is a care-navigation tool, not a diagnostic tool
* Must not diagnose medical conditions
* Must not prescribe treatments
* Must not invent provider or facility information
* Must clearly communicate uncertainty and data limitations
* Must escalate potential emergencies using deterministic safety rules

The text-based navigation workflow is the core product. Voice will be added later as a thin interface over the same application services.

V1 Product Scope

V1 must support:

* Multi-turn text conversations
* Collection of relevant navigation information:
    * User’s care concern
    * City, state, or ZIP code
    * Urgency
    * Derived care category or specialty
* Emergency detection on every user turn
* Facility retrieval from validated CMS-backed data
* Recommendations grounded only in retrieved records
* Explanation of why each facility was returned
* Disclosure when information is missing or unverified
* A FastAPI /v1/chat endpoint
* Health and readiness endpoints
* Automated tests and evaluation cases for:
    * Emergency detection
    * Conversation-state updates
    * Slot collection
    * Facility retrieval
    * Response grounding
    * Structured-output validity

Do not add the following until the text workflow works end to end:

* Appointment booking
* Insurance-network filtering
* Multilingual support
* Voice integration
* Speech-to-text or text-to-speech
* Complex geographic radius search
* A trained ranking model
* Multiple agents

Technology Decisions

Use:

* Python 3.12
* FastAPI for the API layer
* Pydantic for request, response, configuration, and state schemas
* LangGraph only where explicit state-machine orchestration is useful
* PostgreSQL for provider and ingestion metadata
* SQLAlchemy for database access
* Alembic for schema migrations
* Custom retrieval and grounding logic
* pytest for tests
* Ruff for formatting and linting
* mypy for static type checking
* uv for dependency management
* Docker and Docker Compose for local reproducibility

Do not introduce a new framework or infrastructure service unless it solves a demonstrated requirement.

Architecture Principles

Prefer small, explicit, testable components over hidden framework behavior.

Follow these principles:

* Keep API routes thin
* Keep business logic in service modules
* Keep safety rules independent from LLM prompts
* Run emergency detection before ordinary navigation logic
* Treat retrieved provider data as the only source of facility facts
* Do not let the LLM generate facility records
* Use structured schemas for LLM outputs
* Validate all model-generated structured outputs
* Make conversation-state transitions inspectable
* Return an explicit unknown or abstention result when confidence is insufficient
* Keep provider retrieval deterministic and independently testable
* Version safety policies, prompts, retrieval logic, and datasets
* Do not store secrets in source code
* Do not log full conversations or sensitive health information

Avoid:

* Putting all application logic into one agent.py
* Hiding important control flow inside framework abstractions
* Using an LLM as the only emergency detector
* Allowing the LLM to diagnose a condition
* Inventing addresses, phone numbers, ratings, availability, or insurance acceptance
* Continuing routine questioning after an emergency is detected
* Adding voice before the text application is reliable
* Adding tools such as Airflow, Kubernetes, Spark, or MLflow without a concrete need

Safety Behavior

Emergency detection must execute on every user message.

Potential emergency cases include, but are not limited to:

* Chest pain
* Severe difficulty breathing
* Signs of stroke
* Uncontrolled bleeding
* Loss of consciousness
* Suicidal intent or immediate self-harm risk

When an emergency condition is detected:

1. Stop the normal care-navigation workflow.
2. Do not continue collecting routine information.
3. Return the approved emergency-escalation response.
4. Record that an escalation occurred without logging unnecessary sensitive text.
5. Do not rely solely on free-form LLM judgment.

Safety behavior must be covered by deterministic unit tests and golden evaluation cases.

Grounding Requirements

Facility recommendations must come only from provider records returned by the retrieval layer.

Every recommended facility must retain a source record identifier.

The final response must not claim that a facility:

* Accepts a particular insurance plan unless supported by retrieved evidence
* Has appointment availability unless supported by retrieved evidence
* Provides a service not present in the retrieved record
* Has a verified phone number or address when that information is missing
* Is the “best” facility without a defined and explainable ranking basis

When information is unavailable, state that it is unavailable or unverified.

Intended Repository Structure

app/
  main.py
  api/
    routes/
      chat.py
      health.py
  core/
    config.py
    state.py
    policy.py
    versions.py
  schemas/
    chat.py
    provider.py
    safety.py
  services/
    conversation.py
    care_classifier.py
    provider_search.py
    provider_ranker.py
  safety/
    emergency.py
    guardrails.py
  retrieval/
    cms.py
    grounding.py
  llm/
    client.py
    prompts.py
    structured_output.py
  db/
    models.py
    session.py
  observability/
    logging.py
  voice/
    stt.py
    tts.py
data_pipeline/
  ingest_cms.py
  validation.py
  normalization.py
prompts/
  care_classification_v1.txt
  provider_response_v1.txt
  emergency_response_v1.txt
evals/
  emergency_cases.yaml
  slot_filling_cases.yaml
  grounding_cases.yaml
  run_evals.py
tests/
  unit/
  integration/
  safety/
  api/
alembic/

The voice/ directory may remain absent until voice work begins.

Development Rules

Before implementing a change:

1. Identify the component responsible for the behavior.
2. Prefer modifying an existing focused module over creating a broad abstraction.
3. Define or update the relevant Pydantic schema.
4. Add tests for the expected behavior and important failure cases.
5. Run formatting, linting, type checking, and tests.
6. Explain any architectural dependency or new framework before adding it.

Do not rewrite unrelated modules while implementing a focused task.

Do not silently change public API schemas.

Do not add dependencies without explaining their purpose.

Required Commands

Install dependencies:

uv sync

Run the API:

uv run uvicorn app.main:app --reload

Format:

uv run ruff format .

Lint:

uv run ruff check .

Type-check:

uv run mypy app data_pipeline

Run tests:

uv run pytest

Run evaluations:

uv run python -m evals.run_evals

Run locally with containers:

docker compose up --build

Definition of Done

A feature is complete only when:

* Its behavior is implemented in the appropriate module
* Request and response data are validated
* Relevant unit or integration tests pass
* Safety behavior is not weakened
* Grounding requirements remain enforced
* Ruff passes
* mypy passes
* pytest passes
* Public behavior is documented when necessary