# ESGAgent.ai Take-Home Challenge: Ironbark Ridge

Welcome, and thanks for your interest in the Graduate Software Engineer role at ESGAgent.ai.

This challenge is a compressed version of the work we actually do: turning messy, real-world operational data from heavy industry into trustworthy compliance intelligence. There is no single right answer. We have defined a core scope so you know what "done" looks like, but the ceiling is entirely yours. Candidates who go beyond the core scope, in depth, polish, or ideas we didn't ask for, will stand out.

## The Scenario

Ironbark Ridge Resources is a fictional open-cut mine and processing operation in regional Queensland. Their sustainability lead has handed you an export of 18 months of operational data (January 2025 to June 2026) and asked for help understanding their emissions, their safety picture, and the quality of their own data.

Like all real client data, it is messy. Treat everything in the `data/` folder with suspicion. Some of the problems are obvious. Some are not. Part of your job is to find them.

## The Data

| File | What it claims to be |
|---|---|
| `fuel_deliveries.csv` | Fuel delivery invoices by date, quantity, and site area |
| `electricity_meter_readings.csv` | Monthly grid electricity consumption by meter |
| `incident_register.csv` | Safety and environmental incident log with free-text descriptions |
| `suppliers.csv` | Supplier list with categories and annual spend |
| `emission_factors.csv` | Simplified emission factors to convert activity data to kg CO2e (clean, use as-is) |

The emission factors file is deliberately simplified for this exercise. Use it as given; do not go hunting for official NGER factors.

## Core Scope (what "done" looks like)

Build a small full-stack application with four layers:

### 1. Ingestion and database

Write a pipeline that parses the raw files, cleans and normalises them, and loads them into a relational database (PostgreSQL preferred, SQLite acceptable). We care about your schema design and your cleaning decisions. When you find bad data, decide what to do with it: fix, flag, or reject, and be able to justify the choice. Do not silently discard problems.

### 2. Backend API

A Node.js API (framework of your choice) exposing at minimum:

* Monthly emissions by scope (Scope 1 and Scope 2), computed from the cleaned data and the emission factors
* Incident summary and trends (by month, type, severity)
* A **data quality report**: everything you found wrong or suspicious in the source files, in structured form

Include automated tests for the parts you consider most important. We are more interested in which parts you chose to test and why than in coverage numbers.

### 3. AI layer

Use an LLM API (Anthropic or OpenAI, your own key; expected spend is under a few dollars, keep the receipts out of your git history) to do something the raw data cannot do on its own. At minimum:

* Classify the free-text incident descriptions into meaningful safety categories, including identifying any incidents that look like **psychosocial hazards** regardless of how they were originally coded
* Flag incidents where the free-text description appears inconsistent with the recorded severity

Your outputs must be grounded: every AI-generated finding should be traceable back to specific source records. We build compliance software; hallucinated findings are worse than no findings.

### 4. Frontend

A single-page Vue application (or another modern framework if you can argue for it) that presents the insights. We are deliberately not specifying what it should contain. Show us what you think the sustainability lead at Ironbark Ridge most needs to see, and show us your taste. One well-designed screen beats five rushed ones.

### 5. Write-up

A `WRITEUP.md` in your repo covering:

* How to run everything (we will actually run it)
* The data problems you found and what you did about each
* One insight in this data that we did not ask you to find
* How you used AI tools while building this, what they got wrong, and how you caught it
* What you would build next with another week

## Going Beyond

The core scope is the floor. If you have the time and the drive, take it wherever your instincts lead. Past ideas that would impress us include, but are absolutely not limited to: anomaly detection, cross-dataset correlation, a natural-language query interface over the database, an AI-drafted compliance summary with citations, thoughtful CI, containerisation, or something we have never thought of. We would rather see one ambitious idea executed well than a checklist of features.

## Rules and Logistics

* **Time:** The core scope is designed for roughly 6 to 8 hours. There is no deadline pressure beyond what we agree when we send this to you (typically one week). How far beyond the core you go is up to you.
* **AI tools are encouraged.** We are an AI-native company and we expect you to build the way we build. You will be asked in the follow-up interview exactly how you used them.
* **Git history required.** Submit a link to a private GitHub repository (invite the handle we provide) with your real commit history. A single squashed commit tells us nothing about how you work.
* **Your own work.** Use any tools you like, but you must be able to explain and modify every line in your submission. The follow-up interview includes a live change to your codebase.
* **No secrets in the repo.** API keys via environment variables, with a `.env.example`.

## What Happens Next

We review your submission, and if it clears the bar, we book a 30-minute walkthrough where you present your decisions, make a small live change, and talk us through your AI workflow. Strong submissions move fast; we are hiring now.

Good luck. We are genuinely looking forward to seeing what you build.

The ESGAgent.ai team
