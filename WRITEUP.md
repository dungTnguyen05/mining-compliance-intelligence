# Ironbark Ridge Submission Write-up

## Overview

This project turns 18 months of mining operational exports into a traceable compliance intelligence application. It combines a Python ingestion pipeline, PostgreSQL, a TypeScript API, a grounded AI incident-review layer, and a single-page Vue dashboard.

My guiding principle was that compliance software should show uncertainty rather than hide it. I separated safe corrections from unresolved flags, retained the original source files, avoided filling missing activity with invented values, and treated AI output as a review signal rather than a final decision.

## How to run everything

The complete setup guide is in [README.md](README.md). The shortest path is below.

### Prerequisites

- Python 3.11 or newer
- Node.js 20.19 or newer
- PostgreSQL
- npm

### Environment and database

~~~bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
~~~

Create the mining_compliance database and mining_app role, then place the matching credentials in .env. A virtual environment keeps the pipeline dependencies isolated and makes the Python setup reproducible.

### Load operational and AI data

~~~bash
python pipeline/check_data.py
python pipeline/load_data.py
python pipeline/load_ai_findings.py
~~~

The committed AI JSONL can be loaded without a gateway key. If AI findings are regenerated, run the AI loader again afterward.

### Run the API

~~~bash
cd backend
npm ci
npm run typecheck
npm run build
npm test
npm run dev
~~~

### Run the frontend

In a second terminal:

~~~bash
cd frontend
npm ci
npm run build
npm run dev
~~~

Open http://localhost:5173.

### Run Python tests

From the repository root with the virtual environment active:

~~~bash
python -m unittest discover -s pipeline -p "test_*.py"
~~~

## Architecture and data flow

~~~text
CSV exports
    |
    v
inspect -> clean -> validate
    |          |
    |          +----> fixed and flagged quality issues
    v
PostgreSQL
    ^
    |
AI incident JSONL -> schema and grounding validation
    |
    v
Express API -> Vue dashboard
~~~

The raw CSVs are read-only inputs. Cleaning functions create normalized in-memory records, validation produces structured quality issues, and the loader writes both records and decisions to PostgreSQL in a transaction.

The API performs reporting queries rather than duplicating business logic in the browser. The frontend is one decision-focused screen: top-level metrics, emissions and incident trends, AI review signals, evidence-backed priority records, and open quality flags.

## Data problems and decisions

The current checker reports 22 quality issues: 5 corrected during ingestion and 17 retained as flags. No row required rejection after the safe corrections below.

| Dataset | Problem | Decision | Reasoning |
|---|---|---|---|
| electricity readings | MTR-07 drops by roughly 1,000 times from October 2025 onward | fixed 9 rows by multiplying by 1,000 | the sustained step change is consistent with a unit-scale error, not a plausible consumption collapse |
| fuel deliveries | 29 month-only dates | normalized to the first day of the stated month | month is the available reporting precision; the chosen day is explicit and deterministic |
| fuel deliveries | 11 quantities recorded in kL | converted to liters | one unit is required before aggregation and factor application |
| fuel deliveries | 7 exact duplicate rows | removed exact duplicates | retaining them would double-count activity, cost, and Scope 1 emissions |
| fuel deliveries | negative quantity and cost on INV-41777 | corrected both signs | the paired negative values behave like an input sign error rather than a return or credit |
| fuel deliveries | no records for November 2025 | flagged as a missing month | missing fuel activity cannot honestly be interpreted as zero Scope 1 emissions |
| incident register | INC-2025-011 occurs twice with different incidents | preserved both and flagged the duplicate ID | there is not enough evidence to choose a canonical row; source row and record hash preserve identity |
| suppliers | 2 missing ABNs | preserved and flagged | a missing identifier cannot be reconstructed safely |
| suppliers | supplied ABNs fail the Australian checksum or format rules | preserved and flagged | the data is fictional and intentionally does not match real entities, but applying the real validator demonstrates the expected production behavior |
| suppliers | Blackwood spelling variant shares an ABN | preserved and flagged as a duplicate ABN | this may be an entity-resolution issue, but automatically merging suppliers would be destructive |
| emission factors | no quality error found | used as supplied | the challenge explicitly defines this file as clean and simplified |

### Why fix, flag, or reject

I fixed a value only when the evidence supported one deterministic correction. I flagged records where a person still needs to decide what the source should have contained. Rejection was reserved for unusable records; none remained unusable after the supported fixes.

Each issue is stored with its dataset, action, record key, and structured details. This makes the cleaning policy visible through the API and dashboard rather than hiding it in console output.

### Missing November fuel activity

The original implementation could make an absent fuel month look like zero emissions. That is dangerous because a chart could imply excellent Scope 1 performance when the underlying activity was simply not supplied.

The pipeline now detects missing reporting periods and records November 2025 as flagged. The emissions API returns Scope 1 as unavailable for that month, retains the known Scope 2 result, and identifies the missing scope. The dashboard marks the period incomplete instead of fabricating a value.

## Schema decisions

- source_record_hash is the durable key for incident source records, so duplicated business IDs do not overwrite each other
- source_row remains available for a human tracing a finding to the CSV
- incident_ai_findings references the source hash rather than assuming incident_id is unique
- unique meter-period constraints prevent duplicate electricity readings
- checks enforce nonnegative normalized quantities and valid quality actions
- JSONB preserves dataset-specific issue details without flattening useful context
- repeated operational loads replace the reporting dataset so reruns do not accumulate duplicates

## Emissions calculations

Scope 1 is derived from cleaned fuel quantities and the supplied fuel emission factors. Scope 2 is derived from electricity consumption and the supplied Queensland grid factor. The API groups results by month and returns kgCO2e; the dashboard converts to tonnes for presentation.

I did not replace the simplified factors with external NGER factors because the challenge explicitly requires using the supplied values. Reporting completeness is kept separate from calculation: a known scope can still be returned while another scope is marked unavailable.

## AI incident analysis

The AI layer uses the Vercel AI Gateway with openai/gpt-5.4-mini. It classifies the free-text incident description into a controlled hazard taxonomy, identifies psychosocial hazards, proposes a description-based severity when supportable, and returns exact evidence quotes.

The model output is not trusted directly. Python validates, normalizes, compares, versions, checkpoints, and records provenance before a finding is accepted.

### Independent severity review

An early approach showed recorded severity to the model. That encouraged the model to repeat the source label, weakening the inconsistency check.

The production flow withholds recorded severity from the model. The model assesses only what the description supports. Python then compares the independent suggestion with the normalized recorded value and deterministically assigns one of:

- consistent
- appears_inconsistent
- insufficient_context

If the description does not contain enough consequence, treatment, magnitude, or disruption evidence, the output is Not assessed rather than a guessed severity. This is intentionally conservative.

### Reuse without losing record-level meaning

The register contains exact duplicate descriptions. The first occurrence is assessed by the model, and later identical descriptions reuse that assessment. Python still recalculates severity consistency against each record's own recorded severity.

This has two benefits:

- identical text cannot receive contradictory model classifications
- repeated gateway usage and cost are reduced

A reused finding records zero new attempts and the original source record hash. It still receives its own current source context and processing timestamp.

### Grounding and taxonomy validation

A finding is accepted only when its evidence is present in the source description. Category and severity quotes must be exact source substrings.

Additional deterministic rules reject unsupported classifications. For example:

- plant_equipment requires explicit equipment evidence rather than the word plant in a location
- slips_trips_falls requires a described slip, trip, or fall rather than merely mentioning a walkway
- electrical requires an electrical event rather than generator context alone
- work_related_fatigue requires explicit fatigue, tiredness, exhaustion, or sleep evidence
- lack_of_role_clarity requires explicit uncertainty about roles, duties, responsibilities, or expectations
- other cannot be used as an uninformative secondary domain

These rules are deliberately narrow. Missing a weak category is preferable to presenting an unsupported compliance finding.

### Revalidation and analysis versions

Each accepted result includes an analysis version. On a later --all run, saved findings are checked against the current version and validation rules. Findings that no longer meet the standard are reprocessed; valid findings remain checkpointed.

During development, a validation upgrade identified 17 older findings for reprocessing. Because exact descriptions were reused, those records required at most 9 gateway calls. This made stricter validation practical even under free-tier rate limits.

### Provenance

Every finding retains:

- source file, source row, incident ID, description, and source record hash
- model, gateway response ID, processing timestamp, and attempt count
- analysis version
- the originating record hash when an assessment is reused
- normalization decisions applied after model output

A persistent 429 pauses the batch after saving successful work. Rerunning --all resumes only pending or invalid findings.

## How I used AI tools

I used AI in two different roles.

First, the application itself uses an LLM for semantic classification that rules alone cannot perform reliably: meaningful hazard domains, psychosocial identification, and description-based severity review.

Second, I used AI coding tools as a development partner for code drafts, test cases, debugging, output review, and documentation. I worked incrementally, inspected the repository before changes, ran tests after risky edits, and kept the work in small commits and focused pull requests. I also manually compared all 42 source incidents against all 42 generated findings instead of treating a valid JSON response as proof of correctness.

### What the AI got wrong

Human review and validator failures exposed several recurring problems:

- it inferred that a spill was contained merely because a spill kit was deployed
- it assigned Low severity when consequence or magnitude was absent
- it treated wash plant as evidence of a plant-equipment hazard
- it treated walkway as evidence of a slip or trip
- it added environmental or electrical secondary domains from background context
- it added psychosocial types such as job demands, fatigue, or role clarity without explicit evidence
- it sometimes wrote an explanation that contradicted Not assessed
- when recorded severity was visible, it tended to copy it

### How I caught and corrected those problems

- reviewed every AI result beside its source row
- required exact evidence substrings
- added domain-specific and psychosocial evidence rules
- removed recorded severity from the model input
- made severity comparison deterministic in Python
- normalized known unsupported claims and rejected irreconcilable output
- added analysis versioning so older outputs cannot bypass newer rules
- added tests for each failure mode
- preserved model response errors as visible validation failures rather than silently accepting them

This process is why the AI findings should be read as grounded screening signals, not autonomous compliance conclusions.

## Testing choices

The current repository has 44 Python tests and 10 backend tests, plus TypeScript and frontend production builds.

I prioritized tests where a quiet failure would materially change a compliance result:

- unit and date normalization
- exact duplicate removal
- electricity scale correction
- missing reporting-period detection
- source hashing and duplicate incident IDs
- AI response schema and exact quote grounding
- independent severity comparison
- unsupported hazard and psychosocial evidence
- duplicate-description reuse and provenance
- JSONL resume behavior
- AI finding database loading
- Scope 1 and Scope 2 calculations
- missing-scope API behavior
- incident and data-quality API contracts

The tests do not attempt to prove that every model judgment is objectively correct. They prove that accepted outputs follow the defined taxonomy, grounding, provenance, and uncertainty rules.

## Additional insight: the March 2026 operational chain

The dashboard highlights a cross-dataset pattern that was not explicitly requested.

In March 2026, Scope 1 emissions rise by about 44% from February while Scope 2 falls by about 64%. The incident register records a regional substation failure on March 6, followed by roughly three weeks of continuous diesel generator operation. On March 24, multiple crews report fatigue after extended shifts supporting generator operations and manual restarts.

Together, the datasets suggest one operational disruption affected three compliance dimensions:

- the electricity profile changed
- diesel emissions increased
- psychosocial workload and fatigue risk appeared

This is a correlation supported by dated source records, not proof of causation. It is still decision-useful: a sustainability lead can investigate business-continuity planning, backup generation emissions, contractor controls, shift design, and fatigue management as one connected issue.

## Frontend design choices

I chose one information-dense screen instead of several thin pages. The intended reading order is:

1. establish data connection and reporting coverage
2. scan emissions, incident, quality, and AI review totals
3. compare monthly climate and safety performance
4. inspect cross-dataset and AI review signals
5. review grounded source evidence and unresolved data-quality flags

Navigation labels describe the destination: Site overview, Performance, and Review queue. Scroll state keeps the active label synchronized with the visible section, and legacy URL hashes are upgraded.

Charts are data-driven rather than decorative. Hover details expose the month, scope, units, and values. Status cards derive their progress and completeness from API data. AI evidence cards keep the incident ID, source row, location, recorded severity, suggested severity, and exact quote close together.

The visual style uses restrained mining and environmental colors, serif display type, generous spacing, and high-contrast review states. The goal is to feel operational and credible without resembling a generic administration template.

## Limitations and tradeoffs

- the AI taxonomy is domain-informed but not a substitute for a site-approved classification standard
- severity rules are conservative and can return insufficient context even when an investigator knows more outside the description
- supplier duplicates are flagged but not entity-resolved
- the missing fuel month remains unresolved because the source data is absent
- the application has no authentication or role-based review workflow
- JSONL is practical for a small take-home batch but is not a production job system
- the dashboard identifies correlation but does not claim causal inference

## What I would build next with another week

My first priority would be a human review workflow for AI and quality findings. A reviewer should be able to accept, amend, dismiss, assign, and comment on a signal while retaining an immutable audit trail.

I would then add:

1. Docker Compose for PostgreSQL, API, and frontend startup
2. CI for Python tests, backend tests, type checking, and frontend builds
3. database migrations rather than applying one schema file
4. a labeled incident evaluation set with precision and recall by hazard type
5. prompt and taxonomy version history linked to each finding
6. background jobs and rate-limit-aware queues for AI processing
7. supplier entity-resolution suggestions with human approval
8. authentication, roles, and exportable compliance reports
9. configurable completeness thresholds and alerts for missing activity
10. monitoring for ingestion drift, API failures, and model-output rejection rates

The most important next step is not another chart. It is closing the loop between a generated signal, a responsible reviewer, and an auditable decision.
