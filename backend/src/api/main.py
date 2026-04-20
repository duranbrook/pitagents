from fastapi import Depends, FastAPI
from src.api.auth import router as auth_router
from src.api.deps import require_owner

app = FastAPI(title="AutoShop API")

app.include_router(auth_router)


@app.get("/reports")
async def list_reports(current_user: dict = Depends(require_owner)):
    return []
