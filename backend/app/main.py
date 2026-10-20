from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    title="Educator Mapping Demo API",
    version="0.1.0",
    description="基于教育家型教师访谈底库的在线文本量化映射分析平台",
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

app.include_router(analysis_router, prefix="/api")
app.include_router(research_resources_router, prefix="/api")
app.include_router(collection_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
