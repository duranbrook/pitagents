"""Quote management REST API endpoints."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.db.base import get_db
from src.models.quote import Quote

logger = logging.getLogger(__name__)
router = APIRouter(tags=["quotes"])

# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------


class CreateQuoteRequest(BaseModel):
    session_id: str | None = None
    transcript: str | None = None


class LineItem(BaseModel):
    type: str
    description: str
    qty: float
    unit_price: float
    total: float


class QuoteResponse(BaseModel):
    quote_id: str
    status: str
    total: float
    line_items: list[dict]
    session_id: str | None = None
    created_at: str | None = None


class CreateQuoteResponse(BaseModel):
    quote_id: str
    status: str
    total: float
    line_items: list[dict]


class FinalizeQuoteResponse(BaseModel):
    quote_id: str
    status: str
    total: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _generate_line_items(transcript: str) -> tuple[list[dict], float]:
    """Call Claude to extract repair line items from an inspection transcript."""
    client = anthropic.AsyncAnthropic()
    prompt = (
        "You are an auto repair shop estimator. Based on the following vehicle inspection "
        "transcript, generate a repair quote with line items.\n\n"
        f"Transcript:\n{transcript}\n\n"
        "Return a JSON array of line items. Each item must have:\n"
        '- type: "labor" or "part"\n'
        "- description: string\n"
        "- qty: number\n"
        "- unit_price: number (USD)\n"
        "- total: number (qty * unit_price)\n\n"
        "If the transcript is empty or contains no repair-relevant information, return [].\n"
        "Return ONLY valid JSON — no markdown, no explanation."
    )
    response = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    # Strip accidental markdown fences
    if text.startswith("```"):
        text = "\n".join(text.split("\n")[1:])
        text = text.rstrip("`").strip()
    items: list[dict] = json.loads(text)
    total = sum(float(item.get("total", 0)) for item in items)
    return items, total


def _quote_to_response(quote: Quote) -> QuoteResponse:
    return QuoteResponse(
        quote_id=str(quote.id),
        status=quote.status,
        total=float(quote.total) if quote.total is not None else 0.0,
        line_items=list(quote.line_items or []),
        session_id=str(quote.session_id) if quote.session_id else None,
        created_at=quote.created_at.isoformat() if quote.created_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/quotes", response_model=list[QuoteResponse])
async def list_quotes(
    status: Literal["draft", "final", "sent"] | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuoteResponse]:
    """List all quotes, with optional status filter."""
    query = select(Quote)
    if status is not None:
        query = query.where(Quote.status == status)
    result = await db.execute(query)
    quotes = result.scalars().all()
    return [_quote_to_response(q) for q in quotes]


@router.post("/quotes", response_model=CreateQuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_quote(
    body: CreateQuoteRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CreateQuoteResponse:
    """Create a new draft quote, optionally linked to a session."""
    sid = None
    if body.session_id:
        try:
            sid = uuid.UUID(body.session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid session_id: {body.session_id}",
            )

    quote = Quote(session_id=sid)
    db.add(quote)
    await db.commit()
    await db.refresh(quote)

    if body.transcript and body.transcript.strip():
        try:
            items, total = await _generate_line_items(body.transcript)
            quote.line_items = items
            quote.total = total
            await db.commit()
            await db.refresh(quote)
        except Exception:
            logger.exception("Failed to generate line items for quote %s", quote.id)

    return CreateQuoteResponse(
        quote_id=str(quote.id),
        status=quote.status,
        total=float(quote.total) if quote.total is not None else 0.0,
        line_items=list(quote.line_items or []),
    )


@router.get("/quotes/{quote_id}", response_model=QuoteResponse)
async def get_quote(
    quote_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    """Get a quote with all its line items."""
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid quote_id: {quote_id}",
        )

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    return _quote_to_response(quote)


@router.put("/quotes/{quote_id}/finalize", response_model=FinalizeQuoteResponse)
async def finalize_quote(
    quote_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinalizeQuoteResponse:
    """Finalize a draft quote, setting its status to 'final'."""
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid quote_id: {quote_id}",
        )

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    quote.status = "final"
    await db.commit()
    await db.refresh(quote)

    return FinalizeQuoteResponse(
        quote_id=str(quote.id),
        status="final",
        total=float(quote.total) if quote.total is not None else 0.0,
    )


@router.get("/sessions/{session_id}/quote", response_model=QuoteResponse)
async def get_session_quote(
    session_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuoteResponse:
    """Get the quote attached to a session, or 404 if none exists."""
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid session_id: {session_id}",
        )

    result = await db.execute(select(Quote).where(Quote.session_id == sid))
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No quote found for this session",
        )

    return _quote_to_response(quote)
