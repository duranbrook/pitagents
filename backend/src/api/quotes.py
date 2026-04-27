"""Quote management REST API endpoints."""

from __future__ import annotations

import json
import logging
import uuid
from typing import Literal

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.db.base import get_db
from src.models.quote import Quote
from src.models.report import Report
from src.models.session import InspectionSession
from src.models.shop import Shop
from src.models.media import MediaFile
from src.services.pdf import PDFService
from src.storage.s3 import StorageService

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
    pdf_url: str | None = None
    report_id: str | None = None
    report_pdf_url: str | None = None
    share_token: str | None = None


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


async def _analyze_media_for_findings(
    transcript: str,
    media_files: list,
) -> list[dict]:
    """Use extract_repair_findings with presigned URLs so Claude can see the photos."""
    from urllib.parse import urlparse
    from src.tools.extract_findings import extract_repair_findings

    _storage = StorageService()
    photo_s3_urls: list[str] = []
    photo_presigned: list[str] = []
    for m in media_files:
        if m.media_type != "photo" or not m.s3_url or not m.s3_url.startswith("http"):
            continue
        try:
            key = urlparse(m.s3_url).path.lstrip("/")
            presigned = await _storage.presigned_url(key, expires=3600)
            photo_s3_urls.append(m.s3_url)
            photo_presigned.append(presigned)
        except Exception:
            photo_s3_urls.append(m.s3_url)
            photo_presigned.append(m.s3_url)

    if not photo_presigned:
        return []

    result = await extract_repair_findings(
        transcript,
        image_urls=photo_presigned,
        image_s3_urls=photo_s3_urls,
    )
    return result.get("findings", [])


def _summarize_findings(findings: list[dict]) -> str:
    high = sum(1 for f in findings if f.get("severity") == "high")
    med = sum(1 for f in findings if f.get("severity") == "medium")
    parts = []
    if high:
        parts.append(f"{high} urgent issue{'s' if high > 1 else ''}")
    if med:
        parts.append(f"{med} item{'s' if med > 1 else ''} to monitor")
    return f"Inspection found {', '.join(parts)}." if parts else "Inspection complete."


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


@router.get("/quotes/{quote_id}/pdf")
async def get_quote_pdf(
    quote_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and stream the estimate PDF — public, no auth required."""
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invalid quote_id: {quote_id}")

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    session_obj: InspectionSession | None = None
    if quote.session_id:
        r2 = await db.execute(select(InspectionSession).where(InspectionSession.id == quote.session_id))
        session_obj = r2.scalar_one_or_none()

    # Load shop from session → vehicle snapshot (best-effort)
    shop_obj: Shop | None = None
    if session_obj and session_obj.shop_id:
        try:
            r3 = await db.execute(select(Shop).where(Shop.id == session_obj.shop_id))
            shop_obj = r3.scalar_one_or_none()
        except Exception:
            pass

    shop = {
        "name": shop_obj.name if shop_obj else "AutoShop",
        "address": shop_obj.address if shop_obj else "",
        "phone": "",
    }
    vehicle_snapshot = (session_obj.vehicle or {}) if session_obj else {}
    session_dict = {
        "vehicle": vehicle_snapshot,
        "transcript": (session_obj.transcript or "") if session_obj else "",
    }
    quote_dict = {
        "line_items": list(quote.line_items or []),
        "total": float(quote.total or 0),
    }

    try:
        pdf_bytes = PDFService.generate_estimate(quote_dict, session_dict, shop)
    except Exception:
        logger.exception("PDF generation failed for quote %s", quote_id)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="estimate-{quote_id[:8]}.pdf"'},
    )


@router.put("/quotes/{quote_id}/finalize", response_model=FinalizeQuoteResponse)
async def finalize_quote(
    quote_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FinalizeQuoteResponse:
    """Finalize a draft quote, setting its status to 'final'."""
    try:
        qid = uuid.UUID(quote_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail=f"Invalid quote_id: {quote_id}")

    result = await db.execute(select(Quote).where(Quote.id == qid))
    quote = result.scalar_one_or_none()
    if quote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

    quote.status = "final"
    await db.commit()
    await db.refresh(quote)

    # ── Load related objects ──
    session_obj: InspectionSession | None = None
    if quote.session_id:
        r2 = await db.execute(select(InspectionSession).where(InspectionSession.id == quote.session_id))
        session_obj = r2.scalar_one_or_none()

    shop_obj: Shop | None = None
    shop_id_str = current_user.get("shop_id")
    if shop_id_str:
        try:
            sid = uuid.UUID(shop_id_str)
            r3 = await db.execute(select(Shop).where(Shop.id == sid))
            shop_obj = r3.scalar_one_or_none()
        except ValueError:
            pass
    shop = {
        "name": shop_obj.name if shop_obj else "AutoShop",
        "address": shop_obj.address if shop_obj else "",
        "phone": "",
    }

    session_dict: dict = {}
    vehicle_snapshot: dict = {}
    if session_obj:
        vehicle_snapshot = session_obj.vehicle or {}
        session_dict = {"vehicle": vehicle_snapshot, "transcript": session_obj.transcript or ""}

    # ── Upsert Report row ──
    report_obj: Report | None = None
    if session_obj:
        rr = await db.execute(select(Report).where(Report.session_id == session_obj.id))
        report_obj = rr.scalar_one_or_none()

    vehicle_id_val: uuid.UUID | None = None
    vid_str = vehicle_snapshot.get("vehicle_id")
    if vid_str:
        try:
            vehicle_id_val = uuid.UUID(vid_str)
        except ValueError:
            pass

    year  = vehicle_snapshot.get("year", "")
    make  = vehicle_snapshot.get("make", "")
    model_name = vehicle_snapshot.get("model", "")
    title = f"{year} {make} {model_name} — Inspection".strip(" —")

    if session_obj:
        if report_obj is None:
            report_obj = Report(
                session_id=session_obj.id,
                vehicle_id=vehicle_id_val,
                title=title,
                summary="",
                findings=[],
                estimate={"line_items": list(quote.line_items or [])},
                estimate_total=quote.total,
                vehicle=vehicle_snapshot,
                status="final",
            )
            db.add(report_obj)
            await db.commit()
            await db.refresh(report_obj)
        else:
            report_obj.vehicle_id = vehicle_id_val
            report_obj.title = title
            report_obj.estimate = {"line_items": list(quote.line_items or [])}
            report_obj.estimate_total = quote.total
            report_obj.vehicle = vehicle_snapshot
            report_obj.status = "final"
            await db.commit()
            await db.refresh(report_obj)

    # ── Gather media files (objects, not just URLs — presigning happens inside) ──
    media_files_list: list = []
    if session_obj:
        mr = await db.execute(select(MediaFile).where(MediaFile.session_id == session_obj.id))
        media_files_list = list(mr.scalars().all())

    # ── Run Claude multimodal to associate photos with findings ──
    if report_obj and media_files_list and session_obj:
        try:
            findings = await _analyze_media_for_findings(
                transcript=session_obj.transcript or "",
                media_files=media_files_list,
            )
            if findings:
                report_obj.findings = findings
                report_obj.summary = _summarize_findings(findings)
                await db.commit()
                await db.refresh(report_obj)
        except Exception:
            logger.exception("Claude multimodal analysis failed for quote %s", quote_id)

    # ── Generate PDFs ──
    quote_dict = {
        "line_items": list(quote.line_items or []),
        "total": float(quote.total or 0),
    }
    report_dict: dict = {}
    if report_obj:
        report_dict = {
            "id": str(report_obj.id),
            "summary": report_obj.summary or "",
            "findings": list(report_obj.findings or []),
            "estimate": report_obj.estimate or {},
            "estimate_total": float(report_obj.estimate_total or 0),
            "vehicle": report_obj.vehicle or {},
            "share_token": str(report_obj.share_token),
        }

    # Use a backend-served PDF endpoint so no S3 credentials are needed.
    # The /quotes/{id}/pdf endpoint regenerates the PDF on demand from DB state.
    base_url = str(request.base_url).rstrip("/")
    estimate_pdf_url: str | None = f"{base_url}/quotes/{quote_id}/pdf"
    report_pdf_url: str | None = None

    # Validate PDF generation succeeds (log only — don't fail the finalize)
    try:
        PDFService.generate_estimate(quote_dict, session_dict, shop)
    except Exception:
        logger.exception("PDF generation smoke-test failed for quote %s", quote_id)
        estimate_pdf_url = None

    if report_obj and report_dict:
        try:
            PDFService.generate_report(report_dict, media_urls, shop)
            report_pdf_url = f"{base_url}/reports/{report_obj.id}/pdf"
        except Exception:
            logger.exception("Report PDF smoke-test failed for report %s", report_obj.id if report_obj else 'unknown')

    return FinalizeQuoteResponse(
        quote_id=str(quote.id),
        status="final",
        total=float(quote.total or 0),
        pdf_url=estimate_pdf_url,
        report_id=str(report_obj.id) if report_obj else None,
        report_pdf_url=report_pdf_url,
        share_token=str(report_obj.share_token) if report_obj else None,
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
