import json
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.db.practice_models import PracticeExtractionRun, utc_now
from app.engines.practice.engine import EXTRACTION_PROMPT_VERSION, PracticeModel
from app.schemas.practice import Candidate, SourceSelection
from app.services.practice_service import (
    PracticeConflict, PracticeNotFound, PracticeService, checked_spans, fingerprint,
    json_text, normalize_evidence,
)

RUN_TIMEOUT = timedelta(minutes=5)


class PracticeExtractionService:
    def __init__(self, practice: PracticeService, model: PracticeModel | None = None) -> None:
        self.practice = practice
        self.model = model or PracticeModel()

    @staticmethod
    def _run(session, run_id: str) -> PracticeExtractionRun:
        run = session.get(PracticeExtractionRun, run_id)
        if run is None:
            raise PracticeNotFound("抽取任务不存在")
        return run

    @staticmethod
    def _view(run: PracticeExtractionRun) -> dict:
        return {
            "id": run.id, "resource_id": run.resource_id, "status": run.status,
            "attempt": run.attempt, "config": json.loads(run.config_json),
            "error": run.error, "candidates": json.loads(run.result_json).get("candidates", []),
            "created_at": run.created_at.isoformat(),
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "can_retry": run.status in {"queued", "failed"} or bool(
                run.status == "running" and run.started_at and run.started_at < utc_now() - RUN_TIMEOUT
            ),
        }

    def enqueue(self, payload: SourceSelection) -> dict:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            source = self.practice.source(session, payload)
            config = {**self.model.configuration(), "prompt_version": EXTRACTION_PROMPT_VERSION}
            key = fingerprint([source, config])
            row = session.scalar(select(PracticeExtractionRun).where(PracticeExtractionRun.fingerprint == key))
            if row is None:
                row = PracticeExtractionRun(
                    id=str(uuid4()), resource_id=payload.resource_id, fingerprint=key,
                    input_json=json_text(source), config_json=json_text(config),
                )
                session.add(row)
                try:
                    session.commit()
                except IntegrityError:
                    session.rollback()
                    row = session.scalar(select(PracticeExtractionRun).where(PracticeExtractionRun.fingerprint == key))
                    if row is None:
                        raise
            return self._view(row)

    def list_runs(self, resource_id: str = "", limit: int = 30) -> list[dict]:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            statement = select(PracticeExtractionRun)
            if resource_id:
                statement = statement.where(PracticeExtractionRun.resource_id == resource_id)
            return [self._view(row) for row in session.scalars(
                statement.order_by(PracticeExtractionRun.created_at.desc()).limit(limit)
            )]

    def detail(self, run_id: str) -> dict:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            return self._view(self._run(session, run_id))

    def retry(self, run_id: str) -> dict:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            run = self._run(session, run_id)
            if run.status == "queued":
                return self._view(run)
            changed = session.execute(
                update(PracticeExtractionRun)
                .where(PracticeExtractionRun.id == run_id, or_(
                    PracticeExtractionRun.status == "failed",
                    (PracticeExtractionRun.status == "running")
                    & (PracticeExtractionRun.started_at < utc_now() - RUN_TIMEOUT),
                ))
                .values(status="queued", error="", started_at=None, finished_at=None)
                .execution_options(synchronize_session=False)
            )
            if changed.rowcount != 1:
                raise PracticeConflict("该任务正在运行或已完成")
            session.commit()
            session.refresh(run)
            return self._view(run)

    def execute(self, run_id: str) -> None:
        with self.practice.factory() as session:
            claim = session.execute(
                update(PracticeExtractionRun)
                .where(PracticeExtractionRun.id == run_id, PracticeExtractionRun.status == "queued")
                .values(status="running", attempt=PracticeExtractionRun.attempt + 1, started_at=utc_now())
            )
            if claim.rowcount != 1:
                return
            session.commit()
            run = self._run(session, run_id)
            attempt, resource_id = run.attempt, run.resource_id
            source = json.loads(run.input_json)
            config = json.loads(run.config_json)

        status, error, result = "succeeded", "", {}
        try:
            with self.practice.factory() as session:
                self.practice.require_source(session, resource_id)
            model_config = {key: value for key, value in config.items() if key != "prompt_version"}
            if config.get("prompt_version") != EXTRACTION_PROMPT_VERSION:
                raise ValueError("抽取提示版本已更新，请提交新任务")
            output = self.model.extract(source["spans"], model_config)
            for candidate in output.candidates:
                spans = checked_spans(source["spans"], candidate.segment_ids)
                candidate.content.concept_ids = []
                candidate.content.interpretation = ""
                candidate.content.applicability = ""
                normalize_evidence(candidate.content, spans)
            result = output.model_dump()
        except Exception as exc:
            status = "failed"
            error = str(exc)[:1500] if isinstance(exc, ValueError) else "事件抽取失败，请检查模型与任务日志"
        with self.practice.factory() as session:
            session.execute(
                update(PracticeExtractionRun).where(
                    PracticeExtractionRun.id == run_id, PracticeExtractionRun.status == "running",
                    PracticeExtractionRun.attempt == attempt,
                ).values(status=status, error=error, result_json=json_text(result), finished_at=utc_now())
            )
            session.commit()

    def accept(self, run_id: str, candidate_index: int) -> dict:
        with self.practice.factory() as session:
            self.practice.check_schema(session)
            run = self._run(session, run_id)
            candidates = json.loads(run.result_json).get("candidates", [])
            if run.status != "succeeded" or not 0 <= candidate_index < len(candidates):
                raise PracticeNotFound("抽取候选不存在")
            self.practice.require_source(session, run.resource_id)
            candidate = Candidate.model_validate(candidates[candidate_index])
            source = json.loads(run.input_json)
            source["spans"] = checked_spans(source["spans"], candidate.segment_ids)
            key = fingerprint(["extraction", run.id, candidate_index])
            return self.practice.create_from_source(session, source, candidate.content, key)
