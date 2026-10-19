from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from app.schemas.research_resources import (
    ResearchResourceDetail,
    ResearchResourceListResponse,
    ResearchResourceStats,
    ResourceBatchImportResponse,
    ResourceImportJobView,
    ResourceImportResult,
)
from app.services.research_resource_service import (
    MAX_UPLOAD_BYTES,
    ResearchResourceService,
    ResourceImportError,
    ResourceSchemaNotReady,
)


router = APIRouter(tags=["research-resources"])
service = ResearchResourceService()


def _parse_date(value: str) -> date | None:
    if not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="publication_date 必须使用 YYYY-MM-DD 格式") from exc


def _schema_error(exc: ResourceSchemaNotReady) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


@router.get("/research-resources/stats", response_model=ResearchResourceStats)
def get_resource_stats() -> ResearchResourceStats:
    try:
        return service.get_stats()
    except ResourceSchemaNotReady as exc:
        raise _schema_error(exc) from exc


@router.get("/research-resources", response_model=ResearchResourceListResponse)
def list_research_resources(
    keyword: str = "",
    resource_type: str = "",
    educator_name: str = "",
    analysis_status: str = "",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ResearchResourceListResponse:
    try:
        return service.list_resources(
            keyword=keyword,
            resource_type=resource_type,
            educator_name=educator_name,
            analysis_status=analysis_status,
            limit=limit,
            offset=offset,
        )
    except ResourceSchemaNotReady as exc:
        raise _schema_error(exc) from exc


@router.get("/research-resources/{resource_id}", response_model=ResearchResourceDetail)
def get_research_resource(resource_id: str) -> ResearchResourceDetail:
    try:
        resource = service.get_resource(resource_id)
    except ResourceSchemaNotReady as exc:
        raise _schema_error(exc) from exc
    if resource is None:
        raise HTTPException(status_code=404, detail="研究资源不存在")
    return resource


@router.post("/research-resources/import", response_model=ResourceBatchImportResponse)
async def import_research_resources(
    files: list[UploadFile] = File(...),
    title: str = Form(default=""),
    resource_type: str = Form(default="other"),
    authors: str = Form(default=""),
    educator_name: str = Form(default=""),
    source_institution: str = Form(default=""),
    source_url: str = Form(default=""),
    publication_date: str = Form(default=""),
    copyright_status: str = Form(default="unknown"),
    fulltext_allowed: bool = Form(default=False),
    access_level: str = Form(default="restricted"),
    data_version: str = Form(default="1"),
    citation_text: str = Form(default=""),
) -> ResourceBatchImportResponse:
    if not files:
        raise HTTPException(status_code=422, detail="至少选择一个文件")
    parsed_date = _parse_date(publication_date)
    author_names = [item.strip() for item in authors.replace("，", ",").split(",") if item.strip()]
    results: list[ResourceImportResult] = []
    try:
        for upload in files:
            content = await upload.read(MAX_UPLOAD_BYTES + 1)
            file_title = title.strip()
            if len(files) > 1 and file_title:
                file_title = f"{file_title} — {Path(upload.filename or '未命名').stem}"
            try:
                result = service.import_file(
                    filename=upload.filename or "未命名",
                    data=content,
                    media_type=upload.content_type or "",
                    title=file_title,
                    resource_type=resource_type,
                    authors=author_names,
                    educator_name=educator_name,
                    source_institution=source_institution,
                    source_url=source_url,
                    publication_date=parsed_date,
                    copyright_status=copyright_status,
                    fulltext_allowed=fulltext_allowed,
                    access_level=access_level,
                    data_version=data_version,
                    citation_text=citation_text,
                )
            except ResourceImportError as exc:
                result = ResourceImportResult(
                    job_id="",
                    file_name=upload.filename or "未命名",
                    status="failed",
                    error_message=str(exc),
                )
            results.append(result)
    except ResourceSchemaNotReady as exc:
        raise _schema_error(exc) from exc
    finally:
        for upload in files:
            await upload.close()

    return ResourceBatchImportResponse(
        total=len(results),
        succeeded=sum(item.status == "succeeded" for item in results),
        duplicates=sum(item.status == "duplicate" for item in results),
        failed=sum(item.status == "failed" for item in results),
        results=results,
    )


@router.get("/research-import-jobs", response_model=list[ResourceImportJobView])
def list_research_import_jobs(limit: int = Query(default=50, ge=1, le=200)) -> list[ResourceImportJobView]:
    try:
        return service.list_jobs(limit=limit)
    except ResourceSchemaNotReady as exc:
        raise _schema_error(exc) from exc
