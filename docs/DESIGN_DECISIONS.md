# Design Decisions — Zero500

This document answers the questions a technical interviewer will ask about the
Zero500 RAG / incident-investigation architecture. It is written so it can be
read back almost verbatim as talking points, and it doubles as the project's
recorded engineering rationale.

## Scope

Zero500 ingests incident telemetry (logs + metrics), retrieves relevant SRE
runbooks / post-mortems from a vector index, and uses Gemini to produce a
structured root-cause analysis (RCA) with evidence references and a remediation
plan. The retrieval layer is backed by PostgreSQL + `pgvector`; the reasoning
layer uses Google's Gemini models with native JSON-schema constrained output
validated by Pydantic v2.

---

## 1. Chunking strategy

**What we use:** fixed-size character chunking with overlap, implemented in
`backend/app/data/chunking.py`.

- **Chunk size:** 500 characters
- **Overlap:** 50 characters (10%)
- **Method:** deterministic, boundary-aware character slicing

Each chunk emits at most `chunk_size` characters. Consecutive chunks overlap by
`overlap` characters so that no term is split across a boundary without
surrounding context. The final chunk may be shorter than `chunk_size`. Every
character of the input is emitted exactly once across the returned chunks, which
gives us a strict **no-data-loss** property verified by test:

```python
merge_chunks(chunk_text(text, size, overlap), overlap) == text
```

**Fixed-size vs semantic chunking:** We chose fixed-size over semantic
chunking deliberately. Fixed-size is cheap, dependency-free, deterministic, and
easy to reason about in tests and in production. Semantic chunking (splitting on
paragraph or section boundaries) would preserve more meaning per chunk but adds
complexity and an extra embedding/model dependency just to find boundaries —
unjustified for runbooks and post-mortems that are typically short (a few
hundred to a few thousand characters).

**Experimentation:** No formal A/B experimentation across chunk sizes has been
run yet. The 500/50 values are a starting point tuned so that a single relevant
runbook section usually fits within one chunk while the overlap preserves
cross-chunk context. A natural next step is to sweep chunk size against
Retrieval Recall@2 on `EVAL_GROUND_TRUTH` and pick the size that maximizes
recall without blowing up the prompt.

---

## 2. Vector store choice: Postgres + pgvector

**Decision:** Store embeddings in Neon Serverless PostgreSQL with the `pgvector`
extension, using cosine distance (`<=>`) for retrieval.

**Why not a dedicated vector DB (Pinecone / Qdrant / Weaviate)?**

1. **Operational simplicity.** Zero500 is already a relational app: incidents,
   logs, metrics, and runbooks all live in Postgres. Co-locating the vector
   index with the incident data means one database to back up, monitor, and
   operate — no separate vector-cluster SLA, no keep-alive, no cross-service
   networking.
2. **Cost.** On Neon's free tier, Postgres + pgvector is effectively free for a
   portfolio demo. A managed Pinecone/Qdrant/Weaviate instance is a recurring
   cost or a free tier with stricter vector/dimension limits.
3. **Relational + vector in one query.** Retrieval and incident lookup share a
   transaction and connection pool; we don't need to keep a vector DB and a
   Postgres DB eventually consistent.
4. **Good enough recall.** On the current eval suite, Recall@2 is 100% —
   pgvector cosine search retrieves the correct runbook for every tested
   scenario. For a low-volume demo, dedicated vector-DB features (hybrid search,
   filtering, sharding) are not yet worth the operational tax.

**Honest caveat:** "It's free on Neon" is a real engineering tradeoff, not just
a convenience. If the corpus grows to hundreds of thousands of documents or
query latency becomes a concern, a dedicated vector store with approximate
nearest-neighbor (ANN) indexing would be the right next step.

---

## 3. Retrieval: cosine-distance top-k, no reranking

**What happens:** An incident's retrieval query (title + service + top error
log lines) is embedded with `gemini-embedding-001`, then pgvector returns the
top-k (default k=2) runbooks by cosine distance. Those runbooks are injected
into the Gemini prompt as context, and Gemini produces the final `InvestigationReport`.

**Reranking:** None. There is no cross-encoder, no LLM-based reranker, and no
post-retrieval filtering between pgvector and the model.

**Known limitation:** The initial top-k is the final context. If pgvector's
top-2 misses the truly relevant runbook, the model never sees it, and the
report can be poorly grounded. Stated explicitly as a known limitation: add a
reranking step (e.g. a lightweight cross-encoder or a second Gemini pass scoring
retrieved docs against the incident) as the next retrieval improvement. This is
tracked as a next step in `UAT_SANITY_SIGN_OFF.md`.

---

## 4. Embedding model: gemini-embedding-001 at 768 dimensions

**Decision:** Embed runbook / post-mortem chunks with
`gemini-embedding-001` at **768 dimensions** (`output_dimensionality=768`), and
store them in `vector(768)` columns.

**Tradeoff rationale:**

- **Quality:** `gemini-embedding-001` is a strong general-purpose text embedding
  model; 768 dimensions capture enough semantic detail for runbook retrieval
  (Recall@2 = 100% on the eval suite).
- **Cost / latency:** Lower-dimensional embeddings (e.g. 256 or 384) are faster
  to compute and cheaper to store/query, but risk collapsing fine distinctions
  between similar operational failures (e.g. "connection pool exhaustion" vs.
  "query timeout"). 768 is the sweet spot where recall is already saturated on
  our test set.
- **Consistency:** The same model and dimension are used for indexing (seeding)
  and querying, so query and document vectors live in the same space — required
  for cosine distance to be meaningful.

Configuration is centralized in `backend/app/config.py` (`EMBEDDING_MODEL`,
`EMBEDDING_DIMENSIONS`) and read from env, so the dimension can be retuned in
one place without code changes.

---

## 5. Evidence faithfulness (83%) — failure modes and next steps

**Current number:** 83% average evidence faithfulness on the eval suite — the
ratio of cited evidence items that can be traced back to raw telemetry (logs or
metrics snapshot).

**Observed failure modes (categories of unsupported claims):**

1. **Inferred causality stated as fact.** The model sometimes attributes a root
   cause to a deployment or config change that is plausible but not explicitly
   present in the telemetry (e.g. "the rollout introduced the regression" when
   the logs only show the exception).
2. **Over-generalized evidence.** Evidence items cite "metrics" or "logs" at a
   coarse level without quoting the specific line or value that supports the
   claim, so the automated grounding check can't match a token to the raw text.
3. **Hallucinated runbook linkage.** A remediation step references a runbook
   command that wasn't actually in the retrieved context — the model generates a
   plausible-sounding `kubectl`/`helm` command from training memory.
4. **Multi-hop reasoning gaps.** The model connects two telemetry signals that
   are individually present but whose causal link is assumed, not observed.

**What's been tried / is planned:**

- **Stricter grounding prompts:** The system instruction tells Gemini to cite
  specific log lines / metric values and to avoid claims not present in the
  retrieved context.
- **Schema constraints:** Native JSON-schema output + Pydantic v2 validation
  keep the report shape predictable, which limits unstructured confabulation.
- **Planned (not yet implemented):** citation-checking post-processing that
  verifies each `EvidenceItem.source` appears in the raw telemetry before the
  report is returned, and smaller claim units (one fact per evidence item) to
  make grounding easier to verify.

Faithfulness is the highest-leverage metric for improving trust in the system,
and it is explicitly called out as not-yet-100% so reviewers see honest
self-assessment rather than overclaimed performance.

---

## 6. Prompt design

**Structure:** The Gemini investigation prompt has three parts, assembled in
`backend/app/services/investigator.py`:

1. **System instruction** — sets the persona ("Principal Site Reliability
   Engineer"), the job (autonomous RCA correlating live telemetry with
   organizational knowledge), and the citation behavior (cite exact runbook
   commands when available).
2. **Live incident telemetry** — incident ID, title, service, severity,
   description, metrics snapshot (key/value), and application logs with
   timestamps and levels.
3. **Retrieved context** — the top-k runbooks / post-mortems from pgvector,
   each labeled with doc type, title, and similarity score.

**Output constraint:** `response_mime_type="application/json"` with
`response_schema=InvestigationReport`, so Gemini returns native structured JSON
that is validated by Pydantic v2 before reaching the frontend.

**Temperature:** 0.1 — low randomness for deterministic, repeatable diagnoses.

**Evolution:** The prompt started as a single free-form instruction and evolved
toward (a) separating system instruction from user content, (b) adding explicit
citation requirements after the 83% faithfulness findings, and (c) moving to
schema-constrained JSON output so the frontend can render the report without
parsing free text. Few-shot examples are not currently used; adding a few
labeled incident→report pairs is a candidate improvement for diagnosis
consistency.

---

## Related

- [`UAT_SANITY_SIGN_OFF.md`](UAT_SANITY_SIGN_OFF.md) — recorded UAT results and
  the "known limitations / next steps" section referencing this document and the
  83% evidence-faithfulness number.
- [`backend/app/services/investigator.py`](backend/app/services/investigator.py)
  — prompt assembly and investigation orchestration.
- [`backend/app/data/chunking.py`](backend/app/data/chunking.py) — chunking
  implementation and the no-data-loss round-trip property.
