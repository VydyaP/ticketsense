# TicketSense: design notes

## 1. Components

| Component | Where it runs | Responsibility |
| --- | --- | --- |
| React SPA (`frontend/`) | Vercel (static files) | Forms, ticket queue, dashboard. Talks to the API over JSON; never touches the DB. |
| FastAPI app (`backend/app/`) | Docker container on Render | Validation, business logic, prediction, persistence, monitoring endpoints. |
| Model artifact (`backend/app/ml/artifacts/`) | Inside the API process | Two scikit-learn pipelines loaded once at startup with joblib. |
| PostgreSQL | Neon (serverless Postgres) | Tickets, predictions, probabilities, human corrections. |
| Training script (`ml/train.py`) | Developer machine | Produces the artifact, `metrics.json`, confusion matrix and label evidence. |

### Backend layers

```
api/        HTTP only: parse/validate input, map errors to status codes
services/   business logic: predict -> save, filters, stats queries
ml/         model loading and prediction, no web or DB code
models/     SQLAlchemy table definition
schemas/    Pydantic request/response models (the API contract)
core/       config from env vars, DB engine, logging, metrics
```

Each layer can be tested on its own: the model wrapper has unit tests without a DB or HTTP; the API tests exercise everything together.

## 2. Request flow: creating a ticket

1. Browser sends `POST /api/tickets {title, description}`.
2. Middleware assigns a request ID (or reuses `X-Request-ID`), starts a latency timer.
3. Pydantic validates lengths and required fields → 422 with a field-level message if invalid.
4. `TicketService.create_ticket` calls `model_service.predict(title, description)`:
   title and description are joined (exactly as in training), each pipeline runs
   TF-IDF → Logistic Regression → `predict_proba`; the highest probability is the label
   and its value is the "confidence".
5. The ticket row is inserted with both predictions, their confidences and the full
   probability distributions (JSON columns), then committed.
6. The Prometheus counter `ticketsense_ticket_predictions_total{category,priority}` is incremented.
7. Response 201 with the stored ticket; middleware logs one JSON line
   (method, path, status, duration, request ID) and records the latency histogram.

Correcting a category (`PATCH`) stores `corrected_category` **next to** `predicted_category`
rather than overwriting it, so (prediction, correction) pairs remain available as feedback data.
`effective_category` = correction if present, else prediction; filters and stats use it.

## 3. Key decisions and trade-offs

| Decision | Why | Trade-off / alternative |
| --- | --- | --- |
| **TF-IDF + Logistic Regression** | Strong baseline for short text, trains in seconds, <1 ms predictions, ~2 MB artifact, fits a 512 MB free instance, probabilities come for free, easy to explain. | Ignores word order/semantics. A transformer would likely help small classes but needs far more memory and latency. The spec said to go heavier only if it clearly helps; I didn't measure that yet (see README "improve next"). |
| **`class_weight="balanced"`** | One class is 70% of the data; without weighting the model mostly ignores small classes. | Raises recall of small classes at the cost of precision (visible in "Infrastructure & Servers": recall 0.73, precision 0.41). |
| **Macro F1 as the headline metric** | Accuracy is inflated by the dominant class (always guessing it scores 70%). | Reported alongside accuracy and a majority-class baseline so both are visible. |
| **Model loaded in-process** | Simplest possible serving; no extra service. | Model updates need a redeploy; to scale, a separate model service or registry would be better. |
| **Async SQLAlchemy + asyncpg** | Non-blocking DB I/O in an async framework. | Two drivers (asyncpg for the API, psycopg2 for Alembic), derived from one `DATABASE_URL` in `core/config.py` so users configure one variable. |
| **Alembic migrations at container start** | Schema is versioned and always matches the code that is deployed. `set -e` makes a failed migration stop the deploy. | With many replicas you'd run migrations as a separate release step to avoid races. |
| **Tests against real PostgreSQL** | Catches Postgres-specific behaviour and proves the migrations run (the test session migrates down and up). | Needs Docker locally; slightly slower than SQLite. |
| **Fail loudly when the model is missing** | `/predict` returns 503 and `/health` reports `degraded` instead of serving made-up predictions. | The app is unavailable for predictions until fixed, which is the correct behaviour. |
| **One uvicorn worker** | Fits the free tier's memory; Prometheus counters live in process memory, so one process keeps `/metrics` accurate. | Scale horizontally (more instances) rather than with workers; multi-process would need `prometheus_client` multiprocess mode. |
| **Pinned scikit-learn version** | A pickled model is only reliable on the version that created it; the version is saved in the artifact and checked at load. | Upgrading scikit-learn requires retraining. |
| **Categories served by the API** | The frontend reads the class list from `/api/model/metrics`; PATCH rejects unknown categories. A retrain with new labels needs no UI change. | One extra request on page load (cached). |

## 4. Data and labelling

See the README's *Data* section. In short: the Endava dataset is real but anonymized, so the
category names are my interpretation of numeric codes, backed by the top-terms evidence in
`ml/category_evidence.json`; priority depends on an assumption about the urgency scale.
These are the biggest caveats of the project and are stated wherever metrics are shown.

## 5. Observability

- **`GET /health`**: runs `SELECT 1` and checks the model is loaded; 200 `healthy` or 503 `degraded`.
  Used by the Docker `HEALTHCHECK`, Render's health check and the CI smoke test.
- **`GET /metrics`**: `ticketsense_http_requests_total{method,endpoint,status_code}`,
  `ticketsense_http_request_duration_seconds` (histogram), `ticketsense_ticket_predictions_total{category,priority}`,
  `ticketsense_ticket_corrections_total{original_category,corrected_category}`. Endpoints are labelled by
  route template (`/api/tickets/{ticket_id}`) so the number of label values stays bounded.
- **Logs**: one JSON object per line. The request ID is stored in a `ContextVar` by the middleware and
  added to every record by a logging filter, so any log line written during a request can be tied to it.
  The ID is returned in the `X-Request-ID` response header.

## 6. Configuration

All configuration comes from environment variables (`.env.example` lists them):
`DATABASE_URL`, `CORS_ORIGINS`, `ENVIRONMENT`, `LOG_LEVEL`, optional `MODEL_PATH`/`METRICS_PATH`,
`PORT` (set by Render), and `VITE_API_URL` for the frontend build. No secrets live in the repo.

## 7. Known limitations

- Labels are inferred (see section 4); real deployments would train on their own labelled tickets.
- Training text is email-style, anonymized and partly non-English, so short modern tickets
  ("VPN drops") may be classified with lower confidence than the test metrics suggest.
- No authentication: anyone with the URL can create and edit tickets (fine for a demo, not for production).
- Free hosting tiers sleep when idle; the first request after a pause can take ~30–60 s.
