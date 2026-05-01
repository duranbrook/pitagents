import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.auth import router as auth_router
from src.api.sessions import router as sessions_router
from src.api.reports import router as reports_router
from src.api import transcribe
from src.api import upload
from src.api import chat
from src.api import quotes
from src.api import feedback
from src.api import customers
from src.api import vehicles
from src.api import customer_messages
from src.api.shop_settings import router as shop_settings_router
from src.api.job_cards import router as job_cards_router
from src.api.invoices import router as invoices_router
from src.api.labor_lookup import router as labor_lookup_router
from src.api.appointments import router as appointments_router, public_router as booking_router
from src.api.service_reminders import router as reminders_router
from src.api.inventory import router as inventory_router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="AutoShop API")

_default_origins = "http://localhost:3000,http://127.0.0.1:3000"
_allowed_origins = os.getenv("ALLOWED_ORIGINS", _default_origins).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
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
app.include_router(quotes.router)
app.include_router(feedback.router)
app.include_router(customers.router)
app.include_router(vehicles.router)
app.include_router(customer_messages.router)
app.include_router(shop_settings_router)
app.include_router(job_cards_router)
app.include_router(invoices_router)
app.include_router(labor_lookup_router)
app.include_router(appointments_router)
app.include_router(booking_router)
app.include_router(reminders_router)
app.include_router(inventory_router)
