from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.models import CorpusDataset, CorpusRecord


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_migration_preserves_legacy_corpus_tables_and_rows(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    engine = create_engine(f"sqlite:///{database_path.as_posix()}", future=True)
    CorpusDataset.__table__.create(engine)
    CorpusRecord.__table__.create(engine)
    with Session(engine) as session:
        session.add(
            CorpusDataset(
                id="legacy",
                name="Legacy corpus",
                data_kind="analysis",
                domain="test",
                source="database",
            )
        )
        session.add(CorpusRecord(dataset_id="legacy", text="preserve me"))
        session.commit()

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")

    tables = set(inspect(engine).get_table_names())
    assert {
        "educator_persons",
        "research_resources",
        "resource_authors",
        "resource_files",
        "resource_segments",
        "resource_import_jobs",
        "collection_sources",
        "collection_jobs",
        "video_assets",
        "transcripts",
        "personality_evidence",
        "knowledge_query_runs",
        "retrieval_evaluation_runs",
    } <= tables
    with Session(engine) as session:
        assert session.scalar(select(CorpusRecord.text).where(CorpusRecord.dataset_id == "legacy")) == "preserve me"
