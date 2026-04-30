"""Reports CRUD — DB-backed consumer and staff views."""

from __future__ import annotations

import logging
import uuid
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user, require_owner
from src.db.base import get_db
from src.models.media import MediaFile
from src.models.report import Report
from src.models.session import InspectionSession
from src.models.shop import Shop
from src.services.pdf import PDFService
from src.storage.s3 import StorageService

logger = logging.getLogger(__name__)
_storage = StorageService()

router = APIRouter(tags=["reports"])


class SendRequest(BaseModel):
    phone: str | None = None
    email: str | None = None


class EstimateItemPatch(BaseModel):
    part: str
    labor_hours: float
    labor_rate: float
    parts_cost: float


class EstimateUpdateRequest(BaseModel):
    items: list[EstimateItemPatch]


# ---------------------------------------------------------------------------
# Staff views (auth required)
# ---------------------------------------------------------------------------


@router.get("/reports")
async def list_reports(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """List all reports (summary view)."""
    result = await db.execute(select(Report).order_by(Report.created_at.desc()))
    reports = result.scalars().all()
    return [_to_list_item(r) for r in reports]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get full report detail (staff view)."""
    report = await _get_report_or_404(report_id, db)
    return _to_staff_detail(report)


@router.get("/reports/{report_id}/pdf")
async def get_report_pdf(
    report_id: str,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Generate and stream the inspection report PDF — public, no auth required."""
    report = await _get_report_or_404(report_id, db)

    shop_obj: Shop | None = None
    if report.session_id:
        try:
            from src.models.session import InspectionSession as IS
            sr = await db.execute(select(IS).where(IS.id == report.session_id))
            sess = sr.scalar_one_or_none()
            if sess and sess.shop_id:
                r = await db.execute(select(Shop).where(Shop.id == sess.shop_id))
                shop_obj = r.scalar_one_or_none()
        except Exception:
            pass
    shop = {
        "name": shop_obj.name if shop_obj else "AutoShop",
        "address": shop_obj.address if shop_obj else "",
        "phone": "",
    }

    # Build s3_url → presigned_url mapping for all photo media files.
    # Findings store stable original S3 URLs; presigned URLs are generated fresh
    # here each render so the PDF renderer can actually download them.
    media_result = await db.execute(
        select(MediaFile)
        .where(MediaFile.session_id == report.session_id)
        .where(MediaFile.media_type == "photo")
    )
    s3_to_presigned: dict[str, str] = {}
    for mf in media_result.scalars().all():
        if not mf.s3_url or mf.s3_url.startswith("local://"):
            continue
        try:
            key = urlparse(mf.s3_url).path.lstrip("/")
            s3_to_presigned[mf.s3_url] = await _storage.presigned_url(key, expires=3600)
        except Exception:
            logger.warning("Could not generate presigned URL for %s", mf.s3_url)
            s3_to_presigned[mf.s3_url] = mf.s3_url

    # Convert each finding's photo_url from stable S3 URL → presigned for the PDF renderer.
    # Track which S3 URLs are assigned so the unassigned gallery excludes them.
    assigned_s3_urls: set[str] = set()
    findings_for_pdf: list[dict] = []
    for f in (report.findings or []):
        f_copy = dict(f)
        s3_url = f_copy.get("photo_url")
        if s3_url and s3_url in s3_to_presigned:
            f_copy["photo_url"] = s3_to_presigned[s3_url]
            assigned_s3_urls.add(s3_url)
        findings_for_pdf.append(f_copy)

    # Unassigned photos go into the gallery section of the PDF.
    media_urls = [p for s3, p in s3_to_presigned.items() if s3 not in assigned_s3_urls]

    report_dict = {
        "id": str(report.id),
        "summary": report.summary or "",
        "findings": findings_for_pdf,
        "estimate": report.estimate or {},
        "estimate_total": float(report.estimate_total or 0),
        "vehicle": report.vehicle or {},
        "share_token": str(report.share_token),
    }

    try:
        pdf_bytes = PDFService.generate_report(report_dict, media_urls, shop)
    except Exception:
        logger.exception("Report PDF generation failed for report %s", report_id)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="report-{report_id[:8]}.pdf"'},
    )


@router.post("/reports/{report_id}/send")
async def send_report(
    report_id: str,
    body: SendRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    report = await _get_report_or_404(report_id, db)
    report.sent_to = {"phone": body.phone, "email": body.email}
    await db.commit()
    return {"sent_to": report.sent_to}


@router.patch("/reports/{report_id}/estimate")
async def patch_report_estimate(
    report_id: str,
    body: EstimateUpdateRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update estimate line items, deriving labor_cost and total from hours × rate."""
    report = await _get_report_or_404(report_id, db)

    derived_items = []
    for item in body.items:
        labor_cost = round(item.labor_hours * item.labor_rate, 2)
        total = round(labor_cost + item.parts_cost, 2)
        derived_items.append({
            "part": item.part,
            "labor_hours": item.labor_hours,
            "labor_rate": item.labor_rate,
            "labor_cost": labor_cost,
            "parts_cost": item.parts_cost,
            "total": total,
        })

    estimate_total = round(sum(i["total"] for i in derived_items), 2)

    from sqlalchemy import update as sa_update
    await db.execute(
        sa_update(Report)
        .where(Report.id == report.id)
        .values(
            estimate={"line_items": derived_items},
            estimate_total=estimate_total,
        )
    )
    await db.commit()
    await db.refresh(report)

    return _to_staff_detail(report)


# ---------------------------------------------------------------------------
# Consumer view (no auth)
# ---------------------------------------------------------------------------


@router.get("/r/{share_token}")
async def consumer_view(
    share_token: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public consumer-facing report — no auth required."""
    try:
        token_uuid = uuid.UUID(share_token)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    result = await db.execute(select(Report).where(Report.share_token == token_uuid))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    # Gather media URLs from the session
    media_result = await db.execute(
        select(MediaFile).where(MediaFile.session_id == report.session_id)
    )
    media_files = media_result.scalars().all()
    media_urls = [m.s3_url for m in media_files if m.s3_url.startswith("http")]

    return _to_consumer_view(report, media_urls)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_report_or_404(report_id: str, db: AsyncSession) -> Report:
    try:
        rid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    result = await db.execute(select(Report).where(Report.id == rid))
    report = result.scalar_one_or_none()
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


def _to_list_item(r: Report) -> dict:
    return {
        "id": str(r.id),
        "vehicle": r.vehicle or {},
        "summary": r.summary or "",
        "total": float(r.estimate_total or 0),
        "share_token": str(r.share_token),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _to_staff_detail(r: Report) -> dict:
    estimate_data = r.estimate or {}
    line_items = estimate_data.get("line_items", [])
    estimate_rows = []
    for item in line_items:
        if "description" in item:
            # Quote format: {type, description, qty, unit_price, total}
            is_labor = item.get("type", "").lower() == "labor"
            total = float(item.get("total", 0))
            estimate_rows.append({
                "part": item.get("description", ""),
                "labor_hours": float(item.get("qty", 0)) if is_labor else 0.0,
                "labor_cost": total if is_labor else 0.0,
                "parts_cost": 0.0 if is_labor else total,
                "total": total,
            })
        else:
            # Report format: {part, labor_hours/labor_hrs, labor_rate, labor_cost, parts_cost, total/line_total}
            estimate_rows.append({
                "part": item.get("part", ""),
                "labor_hours": float(item.get("labor_hours", item.get("labor_hrs", 0))),
                "labor_rate": float(item.get("labor_rate", 0)),
                "labor_cost": float(item.get("labor_cost", 0)),
                "parts_cost": float(item.get("parts_cost", 0)),
                "total": float(item.get("line_total", item.get("total", 0))),
            })
    return {
        "id": str(r.id),
        "vehicle": r.vehicle or {},
        "summary": r.summary or "",
        "findings": r.findings or [],
        "estimate": estimate_rows,
        "total": float(r.estimate_total or 0),
        "share_token": str(r.share_token),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _to_consumer_view(r: Report, media_urls: list[str]) -> dict:
    # Normalize findings for consumer: {description, severity}
    severity_map = {"high": "urgent", "medium": "moderate", "low": "low"}
    findings = []
    for f in (r.findings or []):
        part = f.get("part", "")
        notes = f.get("notes", "")
        description = f"{part} — {notes}" if notes else part
        raw_sev = (f.get("severity") or "low").lower()
        findings.append({
            "description": description,
            "severity": severity_map.get(raw_sev, raw_sev),
        })

    # Flatten estimate to label/amount pairs
    estimate_data = r.estimate or {}
    estimate_items = [
        {"label": item.get("part", ""), "amount": item.get("line_total", 0)}
        for item in estimate_data.get("line_items", [])
    ]

    return {
        "id": str(r.id),
        "vehicle": r.vehicle or {},
        "summary": r.summary or "",
        "findings": findings,
        "estimate_items": estimate_items,
        "total": float(r.estimate_total or 0),
        "media_urls": media_urls,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
