<div align="center">

# Zero500

### From HTTP 500 to Root Cause

**Autonomous AI Incident Investigation & RCA Platform**

Turn noisy application telemetry into an evidence-backed root-cause investigation, relevant runbooks, and an actionable remediation playbook.

<p>
  <img alt="Python 3.12" src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white" />
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white" />
  <img alt="PostgreSQL and pgvector" src="https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?logo=postgresql&logoColor=white" />
  <img alt="Angular" src="https://img.shields.io/badge/Angular-DD0031?logo=angular&logoColor=white" />
  <img alt="Tailwind CSS and Obsidian UI" src="https://img.shields.io/badge/UI-Tailwind%20%2F%20Obsidian-242424?logo=tailwindcss&logoColor=white" />
  <img alt="MIT License" src="https://img.shields.io/badge/License-MIT-green.svg" />
</p>

</div>

---

## The problem: incident response is a context-gathering problem

A production service starts returning HTTP 500 errors at 2:00 AM. An engineer is left correlating raw logs, stack traces, deployment changes, service dependencies, and operational documentation—often under pressure and with only fragments of the story.

**Zero500 automates the investigation workflow.** It brings incident telemetry together with institutional runbooks and historical post-mortems, retrieves relevant operational knowledge, and uses Gemini to produce a structured root-cause analysis (RCA) with evidence references and suggested remediation steps.

The aim is to move from **“something failed”** to **“here is the likely trigger, how the failure propagated, the affected blast radius, and the evidence supporting the recommendation”** in approximately five seconds on the current evaluation suite.

> Zero500 automates investigation, not unchecked production changes. Its recommendations should be reviewed by an engineer before remediation is executed.

## At a glance

- **Incident ingestion:** Accept alert and telemetry payloads through a versioned webhook API.
- **Grounded retrieval:** Search SRE runbooks and historical post-mortems with PostgreSQL and `pgvector`.
- **Structured reasoning:** Use Gemini with native JSON-schema constrained output and Pydantic v2 validation.
- **Causal timeline:** Present the investigation as **Root Trigger → Propagation → Blast Radius**.
- **SRE workbench:** Explore the remediation playbook, telemetry logs, and retrieved knowledge vectors in a Grafana-inspired interface.
- **Evaluation-first workflow:** Run repeatable ground-truth evaluations and automated UAT probes.
- **Quota protection:** Apply IP-based request limits to AI endpoints and cache repeat investigations for five minutes.

## Core architectural highlights

### Contract-driven AI reports

The investigation pipeline requests structured JSON from the Google Gen AI SDK and validates the result against Pydantic v2 models, including the `InvestigationReport` contract. The report carries fields such as the suspected cause, confidence, supporting evidence, and recommended actions.

Native structured output and schema validation make results predictable for downstream code; **they do not by themselves guarantee factual correctness or eliminate hallucinations**. Zero500 therefore pairs schema enforcement with retrieval grounding, evidence references, and a repeatable evaluation suite.

### Runbook RAG backed by `pgvector`

Runbook and post-mortem content is embedded with `gemini-embedding-001` at **768 dimensions** and stored in Neon Serverless PostgreSQL with the `pgvector` extension. Semantic retrieval uses cosine distance (`<=>`) to find operational guidance relevant to an incident.

Retrieved runbooks can inform concrete recovery suggestions, including commands for tools such as `kubectl`, `helm`, or `psql`, when those commands are supported by the retrieved operational material. Treat generated commands as recommendations to review—not commands to run blindly.

### Interactive causal failure cascade

Instead of showing only a paragraph of model output, Zero500 organizes the diagnosis into a staged timeline:

1. **Root Trigger** — the likely initiating event or fault.
2. **Propagation** — how the initial fault may have affected dependent components.
3. **Blast Radius** — impacted services or user-facing behavior supported by the available telemetry.

This structure helps an engineer inspect the proposed causal chain and distinguish observed facts from inferred explanations.

### Live telemetry webhook

`POST /api/v1/incidents/ingest` accepts incident and alert payloads through the API rather than requiring investigations to be limited to hardcoded demo incidents. Payload mapping may be needed to normalize provider-specific fields from systems such as Prometheus Alertmanager, Datadog, or PagerDuty.

### Grafana-style segmented workbench

The Angular frontend uses standalone components and Signals, with an Obsidian-and-Charcoal SRE war-room theme inspired by operational dashboards. The main work areas are:

- **Remediation Playbook** — investigation summary and recommended next steps.
- **Telemetry Log Explorer** — inspect the incident logs used as evidence.
- **Knowledge Vectors** — inspect the knowledge retrieved from the runbook corpus.

The layout is designed to avoid horizontal overflow and keep key incident evidence visible while navigating the investigation.

## System architecture

```mermaid
flowchart TD
    A[Incoming webhook / telemetry] --> B[FastAPI ingestion API]
    B --> C[(Neon PostgreSQL<br/>incidents and logs)]
    D[SRE runbooks and post-mortems] --> E[Chunking and Gemini embeddings<br/>768 dimensions]
    E --> F[(pgvector knowledge index)]
    C --> G[Investigation orchestrator<br/>parallel context retrieval]
    F --> G
    G --> H[Gemini 3.5 Flash reasoning<br/>native structured JSON output]
    H --> I[Pydantic v2 validation<br/>InvestigationReport]
    I --> J[Angular SRE War Room<br/>causal timeline and evidence]
    J --> K[Evaluation suite and UAT review]
    K -. ground truth and regression feedback .-> G
```

### Technology stack

| Layer | Technology | Responsibility |
|---|---|---|
| API and orchestration | Python 3.12, FastAPI | Versioned REST API and investigation workflow |
| Schema contracts | Pydantic v2 | Request validation and typed investigation reports |
| AI reasoning | Google Gen AI SDK, `gemini-3.5-flash` | Incident analysis and structured RCA generation |
| Embeddings | `gemini-embedding-001` (768 dimensions) | Embed runbook and post-mortem chunks |
| Retrieval and persistence | Neon Serverless PostgreSQL, `pgvector` | Incident/log storage and cosine-distance retrieval via `<=>` |
| Abuse and quota protection | SlowAPI | IP-based rate limiting on AI endpoints |
| Repeat-request optimization | In-memory TTL cache | Cache investigations for five minutes |
| Frontend | Angular, standalone components, Signals | Interactive incident workbench |
| UI styling | Tailwind CSS, Obsidian/Charcoal theme | Responsive SRE dashboard |
| Automated verification | `backend/sanity_check.py` | End-to-end sanity and UAT probes |

## Evaluation and UAT scorecard

The current ground-truth evaluation suite and the recorded UAT sign-off report the following results. See [`UAT_SANITY_SIGN_OFF.md`](UAT_SANITY_SIGN_OFF.md) for the test-run record.

| Metric | Result | What it measures |
|---|---:|---|
| Retrieval Recall@2 | **100%** | Whether the expected target runbook appears in the top two retrieved results across the tested failure scenarios |
| Diagnosis accuracy (LLM-as-a-Judge) | **100%** | Semantic alignment between generated diagnoses and the verified engineering ground truth, as assessed by the configured judge |
| Evidence faithfulness | **83%** | Whether statements in the report are supported by the retrieved evidence and raw telemetry |
| End-to-end latency | **~5.0 s** | Approximate investigation response time for the evaluated scenarios; independent retrieval work is parallelized with Python `ThreadPoolExecutor` |
| Automated sanity / UAT probes | **7/7 passed (100%)** | Result of the automated probes in `backend/sanity_check.py` for the recorded test run |

**How to interpret the numbers:** these are results for the current test suite, not guarantees of performance on every production incident. The diagnosis score uses an LLM-as-a-Judge and should be supplemented with human review as the evaluation set grows. Evidence faithfulness is not 100%; the system should be evaluated and improved on cases where the report is not fully supported. In the recorded suite, citations were checked against raw telemetry and no hallucinated timestamps or metrics were observed.

## Quickstart

### Prerequisites

- Python **3.11+** (Python 3.12 is the target runtime)
- Node.js **18+** and npm
- A Neon PostgreSQL database with the `pgvector` extension enabled
- A Gemini API key from [Google AI Studio](https://aistudio.google.com/)
- Git

> Free-tier APIs and hosting are subject to quotas, eligibility, and provider policy. A free Google AI Pro subscription does not imply unlimited direct Gemini API usage. Keep API billing disabled if a hard zero-spend constraint is required.

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Zero500
```

Replace `<your-repository-url>` with the URL of your repository.

### 2. Configure Neon and environment variables

Create or select a Neon database and enable `pgvector` if it is not already enabled:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Create `backend/.env` with the environment variables expected by the backend configuration. The following names reflect the project's intended settings; keep them aligned with the actual settings module if they differ:

```dotenv
GEMINI_API_KEY=replace_with_your_api_key
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=gemini-embedding-001
EMBEDDING_DIMENSIONS=768
DATABASE_URL=postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require
```

Use your Neon connection string for `DATABASE_URL`. Never commit `.env` files or real secrets. Store deployed secrets in the hosting provider's environment settings and use placeholders in any committed `.env.example`.

### 3. Install and start the backend

```bash
cd backend
python -m venv .venv
```

Activate the environment, then install dependencies:

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

Seed the runbook knowledge base and start the API:

```bash
python -m app.data.seed_runbooks
uvicorn app.main:app --reload --port 8000
```

The API should be available at `http://127.0.0.1:8000`. Interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 4. Install and start the frontend

In a second terminal, from the repository root:

```bash
cd frontend
npm install
npm start
```

Open the local URL printed by the Angular development server, typically `http://localhost:4200`.

### 5. Run automated sanity verification

Start the backend first, ensure the required environment variables and database are configured, then run this command from the repository root:

```bash
python backend/sanity_check.py
```

The recorded UAT run passed **7 out of 7 probes**. Re-run the script after changes to verify the current checkout; results can differ if configuration, quotas, database state, or model behavior changes.

## API reference

All routes below are under the `/api/v1` prefix. Use `http://127.0.0.1:8000/docs` for the live OpenAPI schemas and current request/response details.

| Method and endpoint | Purpose | Notes |
|---|---|---|
| `GET /api/v1/health` | Health check for the API | Useful for local and deployment smoke tests |
| `GET /api/v1/incidents` | List available incidents | Returns incident records available to the application |
| `POST /api/v1/incidents/ingest` | Ingest an incident or alert payload | Normalizes incoming telemetry into an incident record; provider-specific mappings may be needed |
| `POST /api/v1/incidents/{id}/investigate` | Investigate a selected incident | **Rate-limited to 5 requests/minute per IP**; repeat investigations may use the five-minute in-memory cache |
| `GET /api/v1/runbooks/search?query=...` | Search the runbook knowledge base | Uses semantic retrieval over embedded runbook content |
| `POST /api/v1/evaluations/run` | Execute the evaluation suite | **Rate-limited to 2 requests/minute per IP**; intended for controlled evaluation, not unrestricted public triggering |

Example health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Example runbook search:

```bash
curl "http://127.0.0.1:8000/api/v1/runbooks/search?query=database%20connection%20pool%20exhaustion"
```

## Reliability, security, and operational boundaries

- **Rate limits:** SlowAPI applies IP-based limits to AI-intensive endpoints to reduce abuse and protect free-tier quotas.
- **Short-lived cache:** Investigation responses are cached in memory for five minutes to reduce repeat work. This cache is process-local and is cleared when the backend restarts; it is not a durable data store.
- **Secrets:** Keep the Gemini key and database credentials on the server. Never ship secrets in Angular bundles or commit them to Git.
- **Untrusted telemetry:** Treat logs, alert payloads, and retrieved documents as untrusted data. They may contain malformed content or prompt-injection attempts.
- **Evidence before action:** Validate generated output and review supporting evidence before accepting remediation recommendations.
- **Human control:** Do not execute generated `kubectl`, `helm`, `psql`, or other operational commands automatically without explicit authorization and appropriate safeguards.
- **Free-tier constraints:** Public hosting may cold-start, sleep, or enforce quota and resource limits. The project targets a low-volume portfolio demo, not a high-availability production service.

## Project status and milestones

- [x] **Stage 1 — Incident model and ingestion:** synthetic incident records, logs, and webhook-based ingestion.
- [x] **Stage 2 — Knowledge base and retrieval:** runbook seeding, Gemini embeddings, Neon PostgreSQL, and `pgvector` semantic search.
- [x] **Stage 3 — Structured AI investigation:** Gemini 2.5 Flash reasoning, native JSON-schema output, and Pydantic v2 report validation.
- [x] **Stage 4 — Investigation workbench:** causal failure cascade, telemetry explorer, remediation playbook, and knowledge-vector view.
- [x] **Stage 5 — Evaluation and UAT:** ground-truth benchmark suite, evaluation endpoint, and automated sanity probes.
- [x] **Stage 6 — Backend hardening:** request validation, five-minute investigation cache, IP-based rate limiting, and recorded UAT verification.
- [x] **Stage 7 — Public deployment:** deploy the backend to Render and the Angular frontend to Cloudflare Pages; validate environment configuration, hosted database connectivity, cold starts, and public rate limits.

## Repository layout

```text
Zero500/
├── backend/
│   ├── app/
│   │   └── data/
│   │       └── seed_runbooks.py
│   ├── sanity_check.py
│   └── requirements.txt
├── frontend/
├── UAT_SANITY_SIGN_OFF.md
└── README.md
```

This is a high-level map of the main project areas; individual modules may be added as the implementation evolves.

## License

Zero500 is released under the [MIT License](LICENSE).

---

<div align="center">

**Zero500 — From HTTP 500 to Root Cause.**

*Investigate faster. Ground every conclusion in evidence. Make incident response more repeatable.*

</div>