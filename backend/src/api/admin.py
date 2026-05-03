import asyncio
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db

router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN_SECRET = os.getenv("ADMIN_SECRET", "")


def _check_secret(x_admin_secret: str = Header(default="")):
    if not _ADMIN_SECRET or x_admin_secret != _ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/seed")
async def run_seed(x_admin_secret: str = Header(default="")):
    _check_secret(x_admin_secret)

    seed_script = Path(__file__).parent.parent.parent / "scripts" / "seed_demo.py"
    if not seed_script.exists():
        raise HTTPException(status_code=500, detail="Seed script not found")

    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        str(seed_script),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ},
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
    output = stdout.decode()

    if proc.returncode != 0:
        raise HTTPException(status_code=500, detail=output[-3000:])

    return {"status": "ok", "output": output}


@router.post("/fix-passwords")
async def fix_test_passwords(
    x_admin_secret: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """Reset owner@shop.com and tech@shop.com to 'testpass'."""
    _check_secret(x_admin_secret)
    from passlib.context import CryptContext
    ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed = ctx.hash("testpass")
    result = await db.execute(
        text("UPDATE users SET hashed_password = :h WHERE email IN ('owner@shop.com', 'tech@shop.com')"),
        {"h": hashed},
    )
    await db.commit()
    return {"status": "ok", "updated": result.rowcount}
