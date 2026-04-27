"""Single entry point for building an inspection report from a session.

Both the sessions generate-report endpoint and the quotes finalize endpoint
call this so there is exactly one code path for findings extraction,
estimate generation, and report persistence.
"""

from __future__ import annotations

import uuid
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.media import MediaFile
from src.models.report import Report
from src.models.session import InspectionSession
from src.storage.s3 import StorageService
from src.tools.extract_findings import extract_repair_findings
from src.tools.estimate import generate_estimate


async def build_report(session_id: uuid.UUID, db: AsyncSession) -> Report:
    """Run the full inspection pipeline for a session and return the Report.

    Steps:
    1. Load session + media files
    2. Generate presigned URLs for photos (private S3 bucket)
    3. Extract structured findings via Claude (chain-of-thought, per-photo)
    4. Generate cost estimate via Qdrant parts pricing
    5. Upsert the Report row (creates if missing, updates if already exists)
    6. Mark session as complete

    The photo_url stored in each finding is the stable original S3 URL.
    Presigned URLs are generated fresh at PDF render time.
    """
    sess_result = await db.execute(
        select(InspectionSession).where(InspectionSession.id == session_id)
    )
    session = sess_result.scalar_one_or_none()
    if session is None:
        raise ValueError(f"Session {session_id} not found")

    media_result = await db.execute(
        select(MediaFile).where(MediaFile.session_id == session_id)
    )
    media_files = media_result.scalars().all()

    # Generate presigned URLs for photos so Claude can download them.
    # Keep stable S3 URLs separately — those are stored in findings.photo_url.
    _storage = StorageService()
    photo_s3_urls: list[str] = []
    photo_presigned: list[str] = []
    for m in media_files:
        if m.media_type != "photo" or not m.s3_url or m.s3_url.startswith("local://"):
            continue
        if not m.s3_url.startswith("http"):
            continue
        try:
            key = urlparse(m.s3_url).path.lstrip("/")
            presigned = await _storage.presigned_url(key, expires=3600)
            photo_s3_urls.append(m.s3_url)
            photo_presigned.append(presigned)
        except Exception:
            photo_s3_urls.append(m.s3_url)
            photo_presigned.append(m.s3_url)

    transcript = session.transcript or ""

    findings_data = await extract_repair_findings(
        transcript,
        image_urls=photo_presigned or None,
        image_s3_urls=photo_s3_urls or None,
    )

    vehicle = session.vehicle or {}
    labor_rate = float(vehicle.get("labor_rate", 120.0))
    pricing_flag = vehicle.get("pricing_flag", "shop")
    estimate_data = await generate_estimate(
        vehicle, findings_data.get("findings", []), labor_rate, pricing_flag
    )

    vehicle_id_str = vehicle.get("vehicle_id")
    vehicle_uuid = uuid.UUID(vehicle_id_str) if vehicle_id_str else None

    year = vehicle.get("year", "")
    make = vehicle.get("make", "")
    model = vehicle.get("model", "")
    title = f"{year} {make} {model} — Inspection".strip(" —")

    # Upsert: update existing report if one already exists for this session.
    existing = await db.execute(select(Report).where(Report.session_id == session_id))
    report = existing.scalar_one_or_none()

    if report is None:
        report = Report(
            session_id=session_id,
            vehicle_id=vehicle_uuid,
        )
        db.add(report)

    report.vehicle_id = vehicle_uuid
    report.title = title
    report.status = "final"
    report.summary = findings_data.get("summary", "")
    report.findings = findings_data.get("findings", [])
    report.estimate = estimate_data
    report.estimate_total = estimate_data.get("total", 0)
    report.vehicle = vehicle

    session.status = "complete"

    await db.commit()
    await db.refresh(report)
    return report
