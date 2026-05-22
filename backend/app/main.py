from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.schema_patches import ensure_schema_patches
from app.services.minio_storage import ensure_bucket


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await ensure_schema_patches()
    await ensure_bucket()
    yield
    await dispose_engine()


app = FastAPI(title="SparkitTestPlatform", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    from app.core.database import pool_status

    return {"status": "ok", "db_pool": pool_status()}
