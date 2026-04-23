from fastapi import FastAPI
from src.api.auth import router as auth_router
from src.api.sessions import router as sessions_router
from src.api.reports import router as reports_router
from src.api import transcribe
from src.api import upload
from src.api import chat

app = FastAPI(title="AutoShop API")

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(reports_router)
app.include_router(transcribe.router)
app.include_router(upload.router)
app.include_router(chat.router)
