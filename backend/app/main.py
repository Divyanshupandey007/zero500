from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import router,limiter
from app.services.vector_store import vector_store
from app.services.incident_repository import incident_repo

@asynccontextmanager
async def lifespan(app:FastAPI):
    vector_store.init_db()
    incident_repo.seed_initial_incidents_if_empty()
    yield

app=FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero500 - Autonomous Incident Investigation & RCA Platform",
    lifespan=lifespan
)

app.state.limiter=limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)

ALLOWED_ORIGINS=[
    "http://localhost:4200",
    "http://127.0.0.1:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router)