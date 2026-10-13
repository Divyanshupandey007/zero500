from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.routes import router

app=FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Zero500 - Autonomous Incident Investigation & RCA Platform"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router)