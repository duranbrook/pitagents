from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from src.api.deps import get_current_user, require_owner

router = APIRouter(tags=["reports"])

# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_reports: dict[str, dict] = {}
_share_token_index: dict[str, str] = {}  # share_token -> report_id


def seed_test_report() -> None:
    report_id = "test-report-1"
    share_token = "test-share-token-abc"
    _reports[report_id] = {
        "report_id": report_id,
        "session_id": "test-session-1",
        "summary": "Front brakes worn.",
        "estimate_total": 329.0,
        "share_token": share_token,
        "findings": {
            "summary": "Front brakes worn.",
            "findings": [{"part": "Brake pads", "severity": "urgent", "notes": "worn"}],
        },
        "estimate": {"line_items": [], "total": 329.0},
        "vehicle": {"year": "2019", "make": "Honda", "model": "Civic"},
        "media_urls": [],
        "sent_to": {},
    }
    _share_token_index[share_token] = report_id


seed_test_report()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SendRequest(BaseModel):
    phone: str | None = None
    email: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/reports")
async def list_reports(current_user: dict = Depends(require_owner)) -> list[dict]:
    """List all reports (summary view). Requires owner role."""
    return [
        {
            "report_id": r["report_id"],
            "session_id": r["session_id"],
            "summary": r["summary"],
            "estimate_total": r["estimate_total"],
            "share_token": r["share_token"],
        }
        for r in _reports.values()
    ]


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get full report detail. Requires auth."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.get("/r/{share_token}")
async def consumer_view(share_token: str) -> dict:
    """Public consumer view — no auth required."""
    report_id = _share_token_index.get(share_token)
    if report_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _reports[report_id]


@router.post("/reports/{report_id}/send")
async def send_report(
    report_id: str,
    body: SendRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Record where the report was sent. No real Twilio/SendGrid calls in v1."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    sent_to = {"phone": body.phone, "email": body.email}
    report["sent_to"] = sent_to
    return {"sent_to": sent_to}
