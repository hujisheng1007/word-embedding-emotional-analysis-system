# Scripts

This directory stores reusable project scripts.

Current scripts:

- Root-level `start_dev.ps1`
- Root-level `start_dev.bat`
- Root-level `start_llm_service.ps1`
- Root-level `start_llm_service.bat`
- `prepare_educator_interview_dataset.py`

`prepare_educator_interview_dataset.py` extracts the uploaded educator interview DOCX,
normalizes it into import-ready CSV rows, and runs the current analysis pipeline to
generate processed outputs under `data/`.
