# Scripts

This directory stores reusable project scripts.

Current scripts:

- Root-level `start_dev.ps1`
- Root-level `start_dev.bat`
- Root-level `start_llm_service.ps1`
- Root-level `start_llm_service.bat`
- `prepare_educator_interview_dataset.py`
- `sync_csv_to_database.py`
- `migrate_sqlite_to_mysql.py`

`prepare_educator_interview_dataset.py` extracts the uploaded educator interview DOCX,
normalizes it into import-ready CSV rows, and runs the current analysis pipeline to
generate processed outputs under `data/`.

`sync_csv_to_database.py` seeds datasets from `data/samples` and `data/processed`
into the configured database (`DATABASE_URL`) and marks a non-educator corpus as
default when available.

`migrate_sqlite_to_mysql.py` migrates existing project data from SQLite to MySQL.
Example:

```powershell
python scripts/migrate_sqlite_to_mysql.py `
  --target-url "mysql+pymysql://user:password@127.0.0.1:3306/corpus_db" `
  --truncate-target
```
