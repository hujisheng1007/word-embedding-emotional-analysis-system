from fastapi import APIRouter, HTTPException

from app.core.settings import get_settings
from app.schemas.analysis import (
    ActivateFoundationModelProfileRequest,
    AnalysisRequest,
    AnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
    DatasetOption,
    ExplanationRequest,
    ExplanationResponse,
    FoundationModelProfile,
    PublicSource,
    PublicSourceFetchRequest,
    PublicSourceFetchResponse,
    ReferenceLibraryResponse,
    SystemStatusResponse,
)
from app.services.analysis_service import AnalysisService
from app.services.dataset_service import DatasetService
from app.services.foundation_profile_service import get_foundation_profile_service
from app.services.public_data_service import PublicDataService
from app.services.reference_library_service import get_reference_library_service

router = APIRouter(tags=["analysis"])
service = AnalysisService()
public_data_service = PublicDataService(service)
dataset_service = DatasetService()
foundation_profile_service = get_foundation_profile_service()
reference_library_service = get_reference_library_service()


@router.post("/analyze", response_model=AnalysisResult)
def analyze_text(payload: AnalysisRequest) -> AnalysisResult:
    return service.analyze_text(payload)


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
def analyze_batch(payload: BatchAnalysisRequest) -> BatchAnalysisResponse:
    return service.analyze_batch(payload)


@router.post("/explanations/generate", response_model=ExplanationResponse)
def generate_explanation(payload: ExplanationRequest) -> ExplanationResponse:
    return ExplanationResponse(explanation=service.generate_explanation(payload))


@router.get("/datasets", response_model=list[DatasetOption])
def list_datasets() -> list[DatasetOption]:
    return dataset_service.list_datasets()


@router.get("/datasets/default", response_model=BatchAnalysisResponse)
def get_default_dataset() -> BatchAnalysisResponse:
    try:
        return dataset_service.get_default_dataset_analysis()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/datasets/{dataset_id}", response_model=BatchAnalysisResponse)
def get_dataset(dataset_id: str) -> BatchAnalysisResponse:
    try:
        return dataset_service.get_dataset_analysis(dataset_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/reference-library", response_model=ReferenceLibraryResponse)
def get_reference_library() -> ReferenceLibraryResponse:
    return reference_library_service.get_reference_library()


@router.get("/foundation-model/profiles", response_model=list[FoundationModelProfile])
def list_foundation_model_profiles() -> list[FoundationModelProfile]:
    return [FoundationModelProfile(**item) for item in foundation_profile_service.list_profiles()]


@router.post("/foundation-model/activate", response_model=SystemStatusResponse)
def activate_foundation_model_profile(
    payload: ActivateFoundationModelProfileRequest,
) -> SystemStatusResponse:
    try:
        foundation_profile_service.activate_profile(payload.profile_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return get_system_status()


@router.get("/public-sources", response_model=list[PublicSource])
def list_public_sources() -> list[PublicSource]:
    return public_data_service.list_sources()


@router.post("/public-sources/fetch", response_model=PublicSourceFetchResponse)
def fetch_public_source(payload: PublicSourceFetchRequest) -> PublicSourceFetchResponse:
    try:
        return public_data_service.fetch_and_analyze(payload.source_id, payload.limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"公开数据获取失败: {exc}") from exc


@router.get("/system/status", response_model=SystemStatusResponse)
def get_system_status() -> SystemStatusResponse:
    settings = get_settings()
    runtime = foundation_profile_service.get_runtime_config()
    return SystemStatusResponse(
        llm_enabled=settings.llm_enabled,
        llm_model=settings.llm_model,
        llm_base_url=settings.llm_base_url,
        local_llm_model_path=settings.local_llm_model_path,
        foundation_model_enabled=runtime.enabled,
        foundation_model_name=runtime.model_name or runtime.label,
        active_foundation_profile_id=runtime.profile_id,
        foundation_model_ready=runtime.configured,
    )
