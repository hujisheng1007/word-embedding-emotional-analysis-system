from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from app.schemas.collection import (
    CollectionJobCreate, CollectionJobView, CollectionLogView, CollectionSourceView,
    CollectionStats, EducatorPersonView, ManualResourceCreate, ResourceAnalysisView,
    ReviewUpdate, SubtitleImportRequest, VideoView,
    SourceScheduleUpdate,
    TranscriptionJobCreate,
)
from app.services.collection_service import CollectionSchemaNotReady, CollectionService


router = APIRouter(prefix="/collection", tags=["multi-source-collection"])
service = CollectionService()


def _handle_error(exc: Exception) -> HTTPException:
    if isinstance(exc, CollectionSchemaNotReady):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=502, detail=f"采集来源或任务执行失败：{exc}")


@router.get("/sources", response_model=list[CollectionSourceView])
def list_sources() -> list[CollectionSourceView]:
    try:
        return service.list_sources()
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/stats", response_model=CollectionStats)
def get_stats() -> CollectionStats:
    try:
        return service.get_stats()
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.patch("/sources/{source_id}/schedule")
def update_source_schedule(source_id: str, payload: SourceScheduleUpdate) -> dict[str, int | str]:
    try:
        service.update_schedule(source_id, payload.interval_minutes)
        return {"source_id": source_id, "interval_minutes": payload.interval_minutes}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/jobs", status_code=202)
def create_job(payload: CollectionJobCreate, background: BackgroundTasks) -> dict[str, str]:
    try:
        job_id = service.create_job(payload)
        background.add_task(service.run_job, job_id)
        return {"job_id": job_id, "status": "queued"}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/jobs", response_model=list[CollectionJobView])
def list_jobs(limit: int = Query(default=50, ge=1, le=200)) -> list[CollectionJobView]:
    try:
        return service.list_jobs(limit)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/jobs/{job_id}/logs", response_model=list[CollectionLogView])
def list_logs(job_id: str) -> list[CollectionLogView]:
    try:
        return service.list_logs(job_id)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/jobs/{job_id}/pause")
def pause_job(job_id: str) -> dict[str, str]:
    try:
        service.pause_job(job_id)
        return {"job_id": job_id, "status": "pause_requested"}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/jobs/{job_id}/resume", status_code=202)
def resume_job(job_id: str, background: BackgroundTasks) -> dict[str, str]:
    try:
        service.resume_job(job_id)
        background.add_task(service.run_job, job_id)
        return {"job_id": job_id, "status": "queued"}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/people", response_model=list[EducatorPersonView])
def list_people(keyword: str = "") -> list[EducatorPersonView]:
    try:
        return service.list_people(keyword)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.patch("/people/facts/{fact_id}")
def review_fact(fact_id: str, payload: ReviewUpdate) -> dict[str, str]:
    try:
        service.review_fact(fact_id, payload.review_status, payload.corrected_text)
        return {"id": fact_id, "review_status": payload.review_status}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.patch("/people/identities/{identity_id}")
def review_identity(identity_id: str, payload: ReviewUpdate) -> dict[str, str]:
    try:
        service.review_identity(identity_id, payload.review_status)
        return {"id": identity_id, "review_status": payload.review_status}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/videos", response_model=list[VideoView])
def list_videos(keyword: str = "") -> list[VideoView]:
    try:
        return service.list_videos(keyword)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/videos/{video_id}/subtitles", status_code=201)
def import_subtitle(video_id: str, payload: SubtitleImportRequest) -> dict[str, str]:
    try:
        transcript_id = service.import_subtitle(
            video_id, language=payload.language, origin=payload.origin,
            content=payload.content, fetch_from_source=payload.fetch_from_source,
            model_name=payload.model_name, model_version=payload.model_version,
        )
        return {"transcript_id": transcript_id, "status": "pending_review"}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/videos/{video_id}/transcribe", status_code=202)
def transcribe_video(
    video_id: str, payload: TranscriptionJobCreate, background: BackgroundTasks,
) -> dict[str, str]:
    try:
        job_id = service.create_transcription_job(video_id, payload.language, payload.model_name)
        background.add_task(service.run_transcription_job, job_id)
        return {"job_id": job_id, "status": "queued"}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.patch("/transcript-cues/{cue_id}")
def review_cue(cue_id: str, payload: ReviewUpdate) -> dict[str, str]:
    try:
        service.review_cue(cue_id, payload.review_status, payload.corrected_text)
        return {"id": cue_id, "review_status": payload.review_status}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/transcripts/search")
def search_transcripts(
    query: str = "", start_ms: int | None = Query(default=None, ge=0),
    end_ms: int | None = Query(default=None, ge=0),
) -> list[dict]:
    try:
        return service.search_transcript(query, start_ms, end_ms)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/manual-resources", status_code=201)
def register_manual_resource(payload: ManualResourceCreate) -> dict[str, str]:
    try:
        resource_id = service.register_manual_resource(
            source_id=payload.source_id, title=payload.title,
            source_url=str(payload.source_url), resource_type=payload.resource_type,
            educator_name=payload.educator_name, description=payload.description,
            restriction_reason=payload.restriction_reason,
        )
        return {"resource_id": resource_id, "status": "metadata_registered"}
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.post("/resources/{resource_id}/analyze", response_model=ResourceAnalysisView)
def analyze_resource(resource_id: str) -> ResourceAnalysisView:
    try:
        return service.analyze_resource(resource_id)
    except Exception as exc:
        raise _handle_error(exc) from exc


@router.get("/resources/{resource_id}/analysis", response_model=ResourceAnalysisView | None)
def get_analysis(resource_id: str) -> ResourceAnalysisView | None:
    try:
        return service.get_latest_analysis(resource_id)
    except Exception as exc:
        raise _handle_error(exc) from exc
