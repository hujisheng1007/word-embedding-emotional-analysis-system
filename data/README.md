# Data

This directory stores corpus seed files and generated analysis artifacts.

## Important change

The project now uses a **database-first** data strategy:

- Runtime dataset listing and loading come from database (`DATABASE_URL`).
- CSV files under `data/` are seed/import sources, not the only main corpus.
- The educator interview corpus is treated as one domain subset, not the whole corpus.

## Directory structure

- `raw/`: original extracted text and untouched source material derivatives
- `samples/`: import-ready CSV/TXT files
- `processed/`: analysis results and summaries

## Existing educator corpus artifacts

- `raw/educator_interviews_raw.txt`
- `samples/educator_interviews_import.csv`
- `processed/educator_interviews_analysis.csv`
- `processed/educator_interviews_rule_hit_review.csv`
- `processed/educator_interviews_summary.json`

## Seed data into database

1. Configure database in `backend/.env`:
   - `DATABASE_ENABLED=true`
   - `DATABASE_URL=sqlite:///D:/大创/data/app.db` (or PostgreSQL/MySQL URL)
2. Install backend dependencies:
   - `pip install -r backend/requirements.txt`
3. Run seed sync:
   - `python scripts/sync_csv_to_database.py`

After sync, backend APIs (`/api/datasets*`) will read from database first.
