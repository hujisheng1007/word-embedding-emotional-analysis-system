from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas.knowledge import (
    KnowledgeSearchRequest, KnowledgeSearchResponse, RetrievalEvaluationRequest,
    RetrievalEvaluationResponse,
)
from app.services.knowledge_service import KnowledgeSchemaNotReady, KnowledgeService


router = APIRouter(prefix="/knowledge", tags=["knowledge-retrieval"])
service = KnowledgeService()


@router.post("/search", response_model=KnowledgeSearchResponse)
def search(payload: KnowledgeSearchRequest) -> KnowledgeSearchResponse:
    try:
        return service.search(payload)
    except KnowledgeSchemaNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/evaluations", response_model=RetrievalEvaluationResponse)
def evaluate(payload: RetrievalEvaluationRequest) -> RetrievalEvaluationResponse:
    try:
        return service.evaluate(payload)
    except KnowledgeSchemaNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
