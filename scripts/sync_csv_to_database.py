from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.dataset_service import DatasetService  # noqa: E402


def main() -> None:
    service = DatasetService()
    datasets = service.list_datasets()
    if not datasets:
        print("No datasets found. Please put CSV files under data/samples or data/processed.")
        return

    print("Database sync complete (CSV -> database seed).")
    print(f"Total datasets: {len(datasets)}")
    for dataset in datasets:
        default_flag = " (default)" if dataset.is_default else ""
        print(
            f"- {dataset.id}{default_flag}: {dataset.record_count} records, "
            f"kind={dataset.data_kind}, domain={dataset.domain}, source={dataset.source}"
        )


if __name__ == "__main__":
    main()
