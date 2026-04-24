import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.auth import router as auth_router
from src.api.sessions import router as sessions_router
from src.api.reports import router as reports_router
from src.api import transcribe
from src.api import upload
from src.api import chat

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="AutoShop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(reports_router)
app.include_router(transcribe.router)
app.include_router(upload.router)
app.include_router(chat.router)
