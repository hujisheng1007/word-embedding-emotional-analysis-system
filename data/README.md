# Data

This directory stores project datasets and generated analysis artifacts.

## Structure

- `raw/`: original extracted text and untouched source material derivatives
- `samples/`: import-ready CSV or TXT files for demo and frontend upload
- `processed/`: analysis results, summaries, and review files

## Current educator interview dataset

The uploaded file `教育家型教师访谈材料汇总.docx` has been processed into:

- `raw/educator_interviews_raw.txt`
- `samples/educator_interviews_import.csv`
- `processed/educator_interviews_analysis.csv`
- `processed/educator_interviews_rule_hit_review.csv`
- `processed/educator_interviews_summary.json`

`samples/educator_interviews_import.csv` can be imported directly from the frontend
batch upload panel because it includes a `text` column.
