import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import limiter, router
from app.config import settings
from app.logging import set_correlation_id, setup_logging
from app.services.incident_repository import incident_repo
from app.services.vector_store import vector_store

setup_logging()

logger = logging.getLogger("zero500")


@asynccontextmanager
async def lifespan(app: FastAPI):
    vector_store.init_db()
    incident_repo.seed_initial_incidents_if_empty()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero500 - Autonomous Incident Investigation & RCA Platform",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a correlation id to each request and logs request timing."""

    async def dispatch(self, request: Request, call_next):
        cid = request.headers.get("x-request-id") or str(uuid.uuid4())
        set_correlation_id(cid)
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["x-request-id"] = cid
        logger.info(
            "request completed",
            extra={
                "path": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response


app.add_middleware(CorrelationIdMiddleware)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:4200,http://127.0.0.1:4200",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS if origin.strip()],
    allow_origin_regex=r"https://.*\.pages\.dev",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
