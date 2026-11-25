from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.moral import router as moral_router
from app.api.routes.analysis import router as analysis_router
from app.api.routes.collection import router as collection_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.research_resources import router as research_resources_router
from app.services.collection_scheduler import scheduler as collection_scheduler


@asynccontextmanager
async def lifespan(_app: FastAPI):
    collection_scheduler.start()
    try:
        yield
    finally:
        collection_scheduler.stop()

app = FastAPI(
    title="中国经典教育家多模态资料与道德行动研究平台 API",
    version="0.1.0",
    description="面向教育家传记、访谈与公开视听材料的资源整合、证据检索和画像分析平台",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(moral_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(research_resources_router, prefix="/api")
app.include_router(collection_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
