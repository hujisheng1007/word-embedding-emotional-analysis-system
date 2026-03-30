from __future__ import annotations

import argparse
import sys
from pathlib import Path

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.base import Base  # noqa: E402
from app.db.models import CorpusDataset, CorpusRecord  # noqa: E402


DEFAULT_SOURCE_URL = "sqlite:///D:/大创/data/app.db"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate corpus data from SQLite to MySQL for this project.",
    )
    parser.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help=f"Source database URL (default: {DEFAULT_SOURCE_URL})",
    )
    parser.add_argument(
        "--target-url",
        required=True,
        help="Target MySQL URL, e.g. mysql+pymysql://user:password@127.0.0.1:3306/corpus_db",
    )
    parser.add_argument(
        "--truncate-target",
        action="store_true",
        help="Delete target tables data before import.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_engine = create_engine(args.source_url, future=True)
    target_engine = create_engine(args.target_url, future=True, pool_pre_ping=True)

    SourceSession = sessionmaker(bind=source_engine, autoflush=False, autocommit=False, future=True)
    TargetSession = sessionmaker(bind=target_engine, autoflush=False, autocommit=False, future=True)

    Base.metadata.create_all(bind=target_engine)

    with SourceSession() as source_session, TargetSession() as target_session:
        if args.truncate_target:
            target_session.execute(delete(CorpusRecord))
            target_session.execute(delete(CorpusDataset))
            target_session.commit()

        source_datasets = source_session.execute(select(CorpusDataset)).scalars().all()
        source_records = source_session.execute(select(CorpusRecord)).scalars().all()

        # Import datasets first to satisfy FK constraints.
        for item in source_datasets:
            target_session.merge(
                CorpusDataset(
                    id=item.id,
                    name=item.name,
                    description=item.description,
                    file_name=item.file_name,
                    data_kind=item.data_kind,
                    domain=item.domain,
                    source=item.source,
                    is_default=item.is_default,
                    updated_at=item.updated_at,
                )
            )
        target_session.commit()

        if args.truncate_target:
            # Already clean, direct insert with preserved primary keys.
            batch = [
                CorpusRecord(
                    id=item.id,
                    dataset_id=item.dataset_id,
                    text=item.text,
                    category=item.category,
                    level=item.level,
                    score=item.score,
                    keywords_json=item.keywords_json,
                    score_breakdown_json=item.score_breakdown_json,
                    rule_reason=item.rule_reason,
                    llm_explanation=item.llm_explanation,
                    needs_attention=item.needs_attention,
                )
                for item in source_records
            ]
            target_session.bulk_save_objects(batch)
            target_session.commit()
        else:
            # Upsert-like strategy: replace records per dataset to avoid duplicates.
            dataset_ids = [item.id for item in source_datasets]
            for dataset_id in dataset_ids:
                target_session.execute(delete(CorpusRecord).where(CorpusRecord.dataset_id == dataset_id))
            target_session.commit()

            for item in source_records:
                target_session.add(
                    CorpusRecord(
                        id=item.id,
                        dataset_id=item.dataset_id,
                        text=item.text,
                        category=item.category,
                        level=item.level,
                        score=item.score,
                        keywords_json=item.keywords_json,
                        score_breakdown_json=item.score_breakdown_json,
                        rule_reason=item.rule_reason,
                        llm_explanation=item.llm_explanation,
                        needs_attention=item.needs_attention,
                    )
                )
            target_session.commit()

        dataset_count = target_session.execute(select(CorpusDataset)).scalars().all()
        record_count = target_session.execute(select(CorpusRecord)).scalars().all()
        default_ids = [item.id for item in dataset_count if item.is_default]

    print("Migration completed.")
    print(f"Source: {args.source_url}")
    print(f"Target: {args.target_url}")
    print(f"Datasets migrated: {len(dataset_count)}")
    print(f"Records migrated: {len(record_count)}")
    print(f"Default dataset ids: {default_ids}")


if __name__ == "__main__":
    main()
