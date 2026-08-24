# Mining Compliance Intelligence

A full-stack compliance intelligence application for Ironbark Ridge Resources. It turns 18 months of imperfect operational CSV data into traceable emissions, safety, AI incident-review, and data-quality insights.

The application favors transparent uncertainty over false precision: safe corrections are recorded, ambiguous records are flagged, missing activity is not treated as zero, and every AI finding retains its source record and evidence quote.

## What it delivers

- monthly Scope 1 and Scope 2 emissions from cleaned activity data
- incident summaries and monthly trends by type and severity
- a structured report of fixed and unresolved data-quality issues
- grounded AI classification of incident descriptions, including psychosocial hazards
- independent checks for conflicts between recorded and description-based severity
- a single-page decision dashboard for sustainability leadership
- a cross-dataset signal connecting the March 2026 power outage, emissions shift, and fatigue reports

## Technology

| Layer | Technology |
|---|---|
| ingestion and validation | Python, pandas, JSON Schema |
| database | PostgreSQL |
| API | Node.js, Express, TypeScript |
| AI | Vercel AI Gateway, OpenAI GPT-5.4 mini |
| frontend | Vue 3, Vite, TypeScript |
| testing | Python unittest, Node test runner |

## Architecture

~~~text
raw CSV files
    |
    v
Python cleaning + validation ----> structured data-quality issues
    |
    v
PostgreSQL <---- grounded AI JSONL + provenance
    |
    v
Express/TypeScript API
    |
    v
Vue decision dashboard
~~~

Raw files remain unchanged. Cleaned records, quality decisions, and AI findings are separate so reviewers can trace how each result was produced.

## Prerequisites

- Python 3.11 or newer
- Node.js 20.19 or newer
- npm
- PostgreSQL
- a Vercel AI Gateway key only if regenerating AI findings

The committed AI findings can be loaded without an API key, so an evaluator does not need to spend money to run the application.

## Setup

Run these commands from the repository root.

### 1. Create a Python environment

~~~bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
~~~

A project-local virtual environment keeps Python dependencies isolated from the system installation.

### 2. Configure environment variables

~~~bash
cp .env.example .env
~~~

Update the database password and any other local values in .env. Do not commit this file.

~~~dotenv
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mining_compliance
DB_USER=mining_app
DB_PASSWORD=your_local_password
API_PORT=3000
AI_GATEWAY_API_KEY=
AI_MODEL=openai/gpt-5.4-mini
AI_GATEWAY_BASE_URL=https://ai-gateway.vercel.sh/v1
~~~

### 3. Create the PostgreSQL database

One local setup option is:

~~~sql
CREATE USER mining_app WITH PASSWORD 'your_local_password';
CREATE DATABASE mining_compliance OWNER mining_app;
~~~

Run those statements as a PostgreSQL administrator, then ensure the same credentials are present in .env.

### 4. Check and load the data

~~~bash
python pipeline/check_data.py
python pipeline/load_data.py
python pipeline/load_ai_findings.py
~~~

The first command prints the cleaning and validation decisions without loading the database. The second applies the schema and loads cleaned operational data. The final command loads the committed, grounded AI findings.

pipeline/load_data.py replaces previously loaded operational records for a repeatable run, so run pipeline/load_ai_findings.py afterward whenever the operational data is reloaded.

### 5. Start the API

From backend/:

~~~bash
npm ci
npm run typecheck
npm run build
npm test
npm run dev
~~~

The API listens on http://localhost:3000 by default. GET /health confirms that it is running.

### 6. Start the frontend

In a separate terminal:

~~~bash
cd frontend
npm ci
npm run build
npm run dev
~~~

Open http://localhost:5173. Vite proxies /api requests to the backend on port 3000 during development.

## AI regeneration

Regeneration is optional because the reviewed JSONL output is committed.

To analyze one incident:

~~~bash
python pipeline/ai_incident_analysis.py --incident-id INC-2025-127
~~~

To process or resume the complete register:

~~~bash
python pipeline/ai_incident_analysis.py --all
~~~

Batch processing checkpoints every successful result. A later run reuses valid findings, resumes pending records, and pauses safely after a persistent gateway rate limit. Identical descriptions reuse one model assessment while Python recalculates severity consistency for the current source record.

After regenerating the JSONL file, load it into PostgreSQL:

~~~bash
python pipeline/load_ai_findings.py
~~~

## Tests

Run the Python suite from the repository root:

~~~bash
python -m unittest discover -s pipeline -p "test_*.py"
~~~

Run backend verification from backend/:

~~~bash
npm run typecheck
npm run build
npm test
~~~

Run the frontend production build from frontend/:

~~~bash
npm run build
~~~

The current suite contains 44 Python tests and 10 backend tests. It focuses on cleaning decisions, schema constraints, grounded AI validation, reuse and provenance, emissions calculations, missing-period behavior, and API contracts.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | /health | service and database health |
| GET | /api/emissions/monthly | monthly Scope 1 and Scope 2 emissions |
| GET | /api/incidents/summary | incident totals by type and severity |
| GET | /api/incidents/trends | monthly incident trends |
| GET | /api/incidents/ai-findings | grounded findings with source context |
| GET | /api/incidents/ai-summary | psychosocial and severity-review counts |
| GET | /api/data-quality | fixed, flagged, and rejected source issues |

For the missing November 2025 fuel period, the emissions API returns an unavailable Scope 1 value rather than inventing a zero. Scope 2 remains available and the response identifies the missing scope.

## Repository structure

~~~text
backend/                 Express API, repositories, and tests
data/raw/                unchanged client exports
data/processed/          reviewed AI findings and failure checkpoints
database/schema.sql      PostgreSQL schema and constraints
docs/                    documentation index
frontend/                Vue decision dashboard
pipeline/                cleaning, validation, AI analysis, loading, and tests
.env.example             safe configuration template
ASSIGNMENT.md            original challenge brief
README.md                setup and technical reference
WRITEUP.md               design decisions and submission reflection
~~~

## Trust and traceability

- raw input files are never overwritten
- every quality issue records whether it was fixed, flagged, or rejected
- source rows and record hashes distinguish duplicated business identifiers
- AI evidence quotes must be exact substrings of source descriptions
- recorded severity is withheld from the model and compared afterward in Python
- unsupported categories and psychosocial labels fail validation
- analysis versions force older findings through current validation rules
- AI outputs are screening signals, not final compliance decisions

## Documentation

See [WRITEUP.md](WRITEUP.md) for the complete submission write-up and [docs/README.md](docs/README.md) for the documentation index.
