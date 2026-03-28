from fastapi import APIRouter

from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResult,
    BatchAnalysisRequest,
    BatchAnalysisResponse,
)
from app.services.analysis_service import AnalysisService

router = APIRouter(tags=["analysis"])
service = AnalysisService()


@router.post("/analyze", response_model=AnalysisResult)
def analyze_text(payload: AnalysisRequest) -> AnalysisResult:
    return service.analyze_text(payload)


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
def analyze_batch(payload: BatchAnalysisRequest) -> BatchAnalysisResponse:
    return service.analyze_batch(payload)

