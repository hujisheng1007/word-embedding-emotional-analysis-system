from contextlib import contextmanager

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.schemas.practice import (
    CaseEvaluation, CaseSearch, CreateCase, NewConcept, PublishCase, SaveCase,
    SourceSelection, VersionedAction,
)
from app.services.practice_extraction_service import PracticeExtractionService
from app.services.practice_service import PracticeConflict, PracticeNotFound, PracticeSchemaNotReady, PracticeService
from app.services.training_service import TrainingService

router = APIRouter(prefix="/practice", tags=["practice-knowledge"])
training_router = APIRouter(prefix="/training", tags=["teacher-training"])
practice = PracticeService()
extraction = PracticeExtractionService(practice)
training = TrainingService(practice)


@contextmanager
def translate_errors():
    try:
        yield
    except PracticeNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except PracticeConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except PracticeSchemaNotReady as exc:
        raise HTTPException(503, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/concepts")
def concepts():
    with translate_errors():
        return practice.concepts()


@router.post("/concepts", status_code=201)
def create_concept(payload: NewConcept):
    with translate_errors():
        return practice.create_concept(payload)


@router.get("/cases")
def list_cases(resource_id: str = "", limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    with translate_errors():
        return practice.list_cases(resource_id, limit, offset)


@router.post("/cases", status_code=201)
def create_case(payload: CreateCase):
    with translate_errors():
        return practice.create(payload)


@router.get("/cases/{case_id}")
def case_detail(case_id: str, revision: int | None = Query(None, ge=1)):
    with translate_errors():
        return practice.detail(case_id, revision)


@router.put("/cases/{case_id}/draft")
def save_case(case_id: str, payload: SaveCase):
    with translate_errors():
        return practice.save(case_id, payload)


@router.post("/cases/{case_id}/submit")
def submit_case(case_id: str, payload: VersionedAction):
    with translate_errors():
        return practice.submit(case_id, payload.expected_version)


@router.post("/cases/{case_id}/publish")
def publish_case(case_id: str, payload: PublishCase):
    with translate_errors():
        return practice.publish(case_id, payload)


@router.post("/cases/{case_id}/withdraw")
def withdraw_case(case_id: str, payload: VersionedAction):
    with translate_errors():
        return practice.withdraw(case_id, payload.expected_version)


@router.get("/extractions")
def list_extractions(resource_id: str = "", limit: int = Query(30, ge=1, le=100)):
    with translate_errors():
        return extraction.list_runs(resource_id, limit)


@router.post("/extractions", status_code=202)
def queue_extraction(payload: SourceSelection, background: BackgroundTasks):
    with translate_errors():
        run = extraction.enqueue(payload)
        if run["status"] == "queued":
            background.add_task(extraction.execute, run["id"])
        return run


@router.get("/extractions/{run_id}")
def extraction_detail(run_id: str):
    with translate_errors():
        return extraction.detail(run_id)


@router.post("/extractions/{run_id}/retry", status_code=202)
def retry_extraction(run_id: str, background: BackgroundTasks):
    with translate_errors():
        run = extraction.retry(run_id)
        background.add_task(extraction.execute, run_id)
        return run


@router.post("/extractions/{run_id}/candidates/{index}/accept", status_code=201)
def accept_candidate(run_id: str, index: int):
    with translate_errors():
        return extraction.accept(run_id, index)


@training_router.get("/cases")
def browse_cases(limit: int = Query(20, ge=1, le=50), offset: int = Query(0, ge=0)):
    with translate_errors():
        return training.browse(limit, offset)


@training_router.post("/cases/search")
def search_cases(payload: CaseSearch):
    with translate_errors():
        return training.search(payload)


@training_router.get("/cases/{case_id}")
def training_case(case_id: str, revision: int | None = Query(None, ge=1)):
    with translate_errors():
        return training.case(case_id, revision)


@training_router.get("/cases/{case_id}/graph")
def training_graph(case_id: str, revision: int | None = Query(None, ge=1)):
    with translate_errors():
        return training.graph(case_id, revision)


@training_router.get("/cases/{case_id}/evidence/{evidence_id}")
def training_evidence(case_id: str, evidence_id: str, revision: int = Query(ge=1)):
    with translate_errors():
        return training.evidence(case_id, revision, evidence_id)


@training_router.post("/answers")
def answer(payload: CaseSearch):
    with translate_errors():
        return training.answer(payload)


@router.post("/evaluations")
def evaluate(payload: CaseEvaluation):
    with translate_errors():
        return training.evaluate(payload)
