# Diagnose & Marketing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a CarMD-powered vehicle diagnostic lookup tool and an SMS/email campaign manager to the AutoShop web platform.

**Architecture:** Two independent features sharing the same ShopSettings credentials store. Diagnose is a stateless proxy — the backend calls CarMD on demand and forwards results; no caching layer. Marketing uses a `Campaign` DB model with audience count computed live from job card history.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + httpx (CarMD proxy) + Alembic migrations. Next.js 16 + React 19 + TypeScript + @tanstack/react-query v5. Inline dark styles (`background: '#0d0d0d'`, `color: '#fff'`, amber `#d97706`).

---

## File Map

**Backend — new files:**
- `backend/src/api/diagnose.py` — CarMD proxy router (5 endpoints + add-to-job-card + send-summary)
- `backend/src/models/campaign.py` — Campaign SQLAlchemy model
- `backend/src/api/marketing.py` — Marketing router (CRUD + audience count + send)
- `backend/alembic/versions/<hash>_add_carmd_to_shop_settings.py` — migration adding carmd columns
- `backend/alembic/versions/<hash>_create_campaigns.py` — campaigns table migration
- `backend/tests/test_api/test_diagnose.py`
- `backend/tests/test_api/test_marketing.py`

**Backend — modified files:**
- `backend/src/models/__init__.py` — export Campaign
- `backend/src/api/main.py` — include diagnose_router + marketing_router

**Frontend — new files:**
- `web/app/diagnose/page.tsx` — Diagnose page
- `web/app/marketing/page.tsx` — Marketing page
- `web/components/diagnose/DiagnoseInputBar.tsx`
- `web/components/diagnose/DiagnoseTabs.tsx`
- `web/components/diagnose/DiagnoseActionPanel.tsx`
- `web/components/marketing/CampaignList.tsx`
- `web/components/marketing/ComposePanel.tsx`
- `web/components/marketing/AudienceSelector.tsx`

**Frontend — modified files:**
- `web/lib/types.ts` — DiagnoseResult, Campaign types
- `web/lib/api.ts` — diagnose + marketing API functions
- `web/app/page.tsx` — add Diagnose + Marketing dashboard tiles

---

### Task 1: CarMD proxy endpoints

**Files:**
- Modify: `backend/src/models/shop_settings.py` (add `carmd_api_key`, `carmd_partner_token` — created in Plan 1)
- Create: `backend/alembic/versions/<hash>_add_carmd_to_shop_settings.py`
- Create: `backend/src/api/diagnose.py`
- Modify: `backend/src/api/main.py`
- Create: `backend/tests/test_api/test_diagnose.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_api/test_diagnose.py
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt, os
    token = jwt.encode(
        {"sub": "test-user-id", "shop_id": "test-shop-id"},
        os.environ.get("SECRET_KEY", "test-secret"),
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


def test_diagnose_analyze_returns_results(client, auth_headers):
    fake_carmd = {
        "data": [
            {
                "urgency": 1,
                "urgency_desc": "Critical",
                "desc": "Misfire in cylinder 2",
                "layman_desc": "Engine is misfiring",
                "part": "Ignition Coil",
                "repair": {"difficulty": "Moderate"},
            }
        ]
    }
    with patch("src.api.diagnose._carmd_post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_carmd
        with patch("src.api.diagnose._get_carmd_creds", return_value=("key", "token")):
            resp = client.post(
                "/diagnose/analyze",
                json={"year": 2019, "make": "Toyota", "model": "Camry", "dtcs": ["P0300"]},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    body = resp.json()
    assert "diagnosis" in body
    assert body["diagnosis"][0]["desc"] == "Misfire in cylinder 2"


def test_diagnose_recalls_returns_list(client, auth_headers):
    fake_recalls = {"data": [{"recall_date": "2020-01-01", "component": "Brakes", "consequence": "Loss of braking"}]}
    with patch("src.api.diagnose._carmd_get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_recalls
        with patch("src.api.diagnose._get_carmd_creds", return_value=("key", "token")):
            resp = client.get(
                "/diagnose/recalls",
                params={"year": 2019, "make": "Toyota", "model": "Camry"},
                headers=auth_headers,
            )
    assert resp.status_code == 200
    assert len(resp.json()["recalls"]) == 1


def test_diagnose_no_credentials_raises_422(client, auth_headers):
    with patch("src.api.diagnose._get_carmd_creds", return_value=(None, None)):
        resp = client.post(
            "/diagnose/analyze",
            json={"year": 2019, "make": "Toyota", "model": "Camry", "dtcs": ["P0300"]},
            headers=auth_headers,
        )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend
python -m pytest tests/test_api/test_diagnose.py -v
```

Expected: ImportError or 404 (module doesn't exist yet).

- [ ] **Step 3: Add carmd fields to shop_settings migration**

The `ShopSettings` model was created in Plan 1. Add two new nullable columns via a new migration:

```bash
cd backend
alembic revision --autogenerate -m "add_carmd_to_shop_settings"
```

Edit the generated migration to add only these two columns (remove auto-generated noise):

```python
# in upgrade():
op.add_column('shop_settings', sa.Column('carmd_api_key', sa.String(), nullable=True))
op.add_column('shop_settings', sa.Column('carmd_partner_token', sa.String(), nullable=True))

# in downgrade():
op.drop_column('shop_settings', 'carmd_partner_token')
op.drop_column('shop_settings', 'carmd_api_key')
```

Apply:
```bash
alembic upgrade head
```

- [ ] **Step 4: Update ShopSettings model**

In `backend/src/models/shop_settings.py` (created by Plan 1), add two columns after the existing integration credential fields:

```python
carmd_api_key = Column(String, nullable=True)
carmd_partner_token = Column(String, nullable=True)
```

- [ ] **Step 5: Implement the diagnose router**

```python
# backend/src/api/diagnose.py
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_settings import ShopSettings

router = APIRouter(prefix="/diagnose", tags=["diagnose"])

CARMD_BASE = "https://api.carmd.com/v3.0"


async def _get_carmd_creds(shop_id: str, db: AsyncSession) -> tuple[str | None, str | None]:
    result = await db.execute(select(ShopSettings).where(ShopSettings.shop_id == shop_id))
    settings = result.scalar_one_or_none()
    if not settings:
        return None, None
    return settings.carmd_api_key, settings.carmd_partner_token


async def _carmd_get(path: str, params: dict, api_key: str, partner_token: str) -> dict:
    import base64
    encoded = base64.b64encode(api_key.encode()).decode()
    headers = {
        "content-type": "application/json",
        "authorization": f"Basic {encoded}",
        "partner-token": partner_token,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{CARMD_BASE}{path}", params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def _carmd_post(path: str, body: dict, api_key: str, partner_token: str) -> dict:
    import base64
    encoded = base64.b64encode(api_key.encode()).decode()
    headers = {
        "content-type": "application/json",
        "authorization": f"Basic {encoded}",
        "partner-token": partner_token,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{CARMD_BASE}{path}", json=body, headers=headers)
        resp.raise_for_status()
        return resp.json()


class AnalyzeRequest(BaseModel):
    year: int
    make: str
    model: str
    engine: str | None = None
    mileage: int | None = None
    dtcs: list[str] = []


@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")

    params = {"year": body.year, "make": body.make, "model": body.model}
    if body.engine:
        params["engine"] = body.engine

    diagnosis_data: list = []
    repair_data: list = []

    for dtc in body.dtcs:
        dtc_params = {**params, "dtc": dtc}
        try:
            d = await _carmd_post("/diagnose", dtc_params, api_key, partner_token)
            diagnosis_data.extend(d.get("data", []))
        except httpx.HTTPError:
            pass
        try:
            r = await _carmd_post("/repair", dtc_params, api_key, partner_token)
            repair_data.extend(r.get("data", []))
        except httpx.HTTPError:
            pass

    return {"diagnosis": diagnosis_data, "repair_plan": repair_data}


@router.get("/tsb")
async def get_tsb(
    year: int,
    make: str,
    model: str,
    engine: str | None = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")
    params = {"year": year, "make": make, "model": model}
    if engine:
        params["engine"] = engine
    data = await _carmd_get("/tsb", params, api_key, partner_token)
    return {"tsbs": data.get("data", [])}


@router.get("/recalls")
async def get_recalls(
    year: int,
    make: str,
    model: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")
    params = {"year": year, "make": make, "model": model}
    data = await _carmd_get("/recall", params, api_key, partner_token)
    return {"recalls": data.get("data", [])}


@router.get("/maintenance")
async def get_maintenance(
    year: int,
    make: str,
    model: str,
    mileage: int = 0,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    api_key, partner_token = await _get_carmd_creds(shop_id, db)
    if not api_key or not partner_token:
        raise HTTPException(status_code=422, detail="CarMD credentials not configured")
    params = {"year": year, "make": make, "model": model, "mileage": mileage}
    data = await _carmd_get("/maintainance", params, api_key, partner_token)
    return {"maintenance": data.get("data", [])}


class AddToJobCardRequest(BaseModel):
    job_card_id: str
    diagnosis: list[dict]
    repair_plan: list[dict]


@router.post("/add-to-job-card")
async def add_to_job_card(
    body: AddToJobCardRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    from src.models.job_card import JobCard
    import uuid as _uuid
    result = await db.execute(
        select(JobCard).where(
            JobCard.id == _uuid.UUID(body.job_card_id),
            JobCard.shop_id == shop_id,
        )
    )
    job_card = result.scalar_one_or_none()
    if not job_card:
        raise HTTPException(status_code=404, detail="Job card not found")

    existing_notes = job_card.notes or ""
    diag_summary = "; ".join(d.get("desc", "") for d in body.diagnosis[:3] if d.get("desc"))
    job_card.notes = f"{existing_notes}\n\n[Diagnose] {diag_summary}".strip()

    new_services = list(job_card.services or [])
    for repair in body.repair_plan[:3]:
        desc = repair.get("repair_desc") or repair.get("desc") or ""
        labor = repair.get("labor_hrs") or 0
        if desc:
            new_services.append({"description": desc, "labor_hours": labor, "source": "carmd"})
    job_card.services = new_services

    await db.commit()
    return {"ok": True}


class SendSummaryRequest(BaseModel):
    customer_id: str
    diagnosis: list[dict]


@router.post("/send-summary")
async def send_summary(
    body: SendSummaryRequest,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    # Phase 1 stub — returns the SMS text; real SMS integration in Phase 2
    top_causes = [d.get("layman_desc") or d.get("desc") for d in body.diagnosis[:2] if d]
    summary = "Our inspection found: " + ", ".join(c for c in top_causes if c)
    summary += ". We recommend scheduling a service visit."
    return {"sms_text": summary, "sent": False, "note": "SMS sending not yet configured"}
```

- [ ] **Step 6: Register router in main.py**

In `backend/src/api/main.py`, add after the existing router includes:

```python
from src.api.diagnose import router as diagnose_router
app.include_router(diagnose_router)
```

- [ ] **Step 7: Run tests to verify they pass**

```bash
cd backend
python -m pytest tests/test_api/test_diagnose.py -v
```

Expected: 3 tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/src/api/diagnose.py backend/src/api/main.py \
        backend/src/models/shop_settings.py \
        backend/alembic/versions/ \
        backend/tests/test_api/test_diagnose.py
git commit -m "feat(diagnose): add CarMD proxy endpoints and ShopSettings carmd credentials"
```

---

### Task 2: Campaign model + migration

**Files:**
- Create: `backend/src/models/campaign.py`
- Modify: `backend/src/models/__init__.py`
- Create: `backend/alembic/versions/<hash>_create_campaigns.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_api/test_marketing.py
import pytest
from fastapi.testclient import TestClient
from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers():
    import jwt, os
    token = jwt.encode(
        {"sub": "test-user-id", "shop_id": "test-shop-id"},
        os.environ.get("SECRET_KEY", "test-secret"),
        algorithm="HS256"
    )
    return {"Authorization": f"Bearer {token}"}


def test_list_campaigns_empty(client, auth_headers):
    from unittest.mock import AsyncMock, patch, MagicMock
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    with patch("src.api.marketing.get_db") as mock_db:
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
        resp = client.get("/marketing/campaigns", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_campaign(client, auth_headers):
    from unittest.mock import AsyncMock, patch, MagicMock
    with patch("src.api.marketing.get_db") as mock_db:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_db.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db.return_value.__aexit__ = AsyncMock(return_value=False)
        resp = client.post(
            "/marketing/campaigns",
            json={
                "name": "Summer Promo",
                "message_body": "Hi {first_name}, time for an AC check!",
                "channel": "sms",
                "audience_segment": {"type": "all_customers"},
            },
            headers=auth_headers,
        )
    assert resp.status_code == 201
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
python -m pytest tests/test_api/test_marketing.py -v
```

Expected: ImportError — `src.api.marketing` doesn't exist.

- [ ] **Step 3: Create Campaign model**

```python
# backend/src/models/campaign.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    status = Column(String, nullable=False, default="draft")  # draft/scheduled/active/sent
    message_body = Column(String, nullable=False)
    channel = Column(String, nullable=False, default="sms")  # sms/email/both
    audience_segment = Column(JSON, nullable=False, default=dict)
    send_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    stats = Column(JSON, nullable=False, default=dict)  # sent_count, opened_count, booked_count
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __init__(self, **kwargs):
        kwargs.setdefault("id", uuid.uuid4())
        kwargs.setdefault("status", "draft")
        kwargs.setdefault("channel", "sms")
        kwargs.setdefault("audience_segment", {})
        kwargs.setdefault("stats", {})
        kwargs.setdefault("created_at", datetime.utcnow())
        super().__init__(**kwargs)
```

- [ ] **Step 4: Export Campaign from __init__.py**

In `backend/src/models/__init__.py`, add:

```python
from src.models.campaign import Campaign
```

And add `"Campaign"` to `__all__`.

- [ ] **Step 5: Create migration**

```bash
cd backend
alembic revision --autogenerate -m "create_campaigns"
```

Expected output: new file in `alembic/versions/`. Review to confirm it creates `campaigns` table. Apply:

```bash
alembic upgrade head
```

- [ ] **Step 6: Commit**

```bash
git add backend/src/models/campaign.py backend/src/models/__init__.py backend/alembic/versions/
git commit -m "feat(marketing): add Campaign model and migration"
```

---

### Task 3: Marketing router

**Files:**
- Create: `backend/src/api/marketing.py`
- Modify: `backend/src/api/main.py`

- [ ] **Step 1: Implement marketing router**

```python
# backend/src/api/marketing.py
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.campaign import Campaign

router = APIRouter(prefix="/marketing", tags=["marketing"])

TEMPLATES = [
    {
        "id": "seasonal-promo",
        "name": "Seasonal Promo",
        "message_body": "Hi {first_name}! Summer is here — bring in your {vehicle} for an AC check. Book now: {booking_link}",
    },
    {
        "id": "win-back",
        "name": "Win-Back",
        "message_body": "Hi {first_name}, we miss you! It's been a while since your last visit. Come back in and we'll take care of your {vehicle}.",
    },
    {
        "id": "maintenance-reminder",
        "name": "Maintenance Reminder",
        "message_body": "Hi {first_name}, your {vehicle} is due for {service}. Book online: {booking_link}",
    },
]


class AudienceSegment(BaseModel):
    type: str  # all_customers | by_service | by_last_visit | by_vehicle_type
    service_type: str | None = None
    last_visit_months_start: int | None = None
    last_visit_months_end: int | None = None
    vehicle_type: str | None = None


class CampaignCreate(BaseModel):
    name: str
    message_body: str
    channel: str = "sms"
    audience_segment: dict
    send_at: str | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    message_body: str | None = None
    channel: str | None = None
    audience_segment: dict | None = None
    send_at: str | None = None
    status: str | None = None


class CampaignResponse(BaseModel):
    campaign_id: str
    shop_id: str
    name: str
    status: str
    message_body: str
    channel: str
    audience_segment: dict
    send_at: str | None
    sent_at: str | None
    stats: dict
    created_at: str


def _to_response(c: Campaign) -> CampaignResponse:
    return CampaignResponse(
        campaign_id=str(c.id),
        shop_id=str(c.shop_id),
        name=c.name,
        status=c.status,
        message_body=c.message_body,
        channel=c.channel,
        audience_segment=c.audience_segment or {},
        send_at=c.send_at.isoformat() if c.send_at else None,
        sent_at=c.sent_at.isoformat() if c.sent_at else None,
        stats=c.stats or {},
        created_at=c.created_at.isoformat(),
    )


@router.get("/templates")
async def list_templates():
    return TEMPLATES


@router.get("/campaigns", response_model=list[CampaignResponse])
async def list_campaigns(
    status: str | None = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    q = select(Campaign).where(Campaign.shop_id == shop_id)
    if status:
        q = q.where(Campaign.status == status)
    q = q.order_by(Campaign.created_at.desc())
    result = await db.execute(q)
    return [_to_response(c) for c in result.scalars().all()]


@router.post("/campaigns", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    send_at = datetime.fromisoformat(body.send_at) if body.send_at else None
    campaign = Campaign(
        shop_id=shop_id,
        name=body.name,
        message_body=body.message_body,
        channel=body.channel,
        audience_segment=body.audience_segment,
        send_at=send_at,
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)


@router.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    body: CampaignUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == uuid.UUID(campaign_id), Campaign.shop_id == shop_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "send_at" and value:
            value = datetime.fromisoformat(value)
        setattr(campaign, field, value)
    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)


@router.delete("/campaigns/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == uuid.UUID(campaign_id), Campaign.shop_id == shop_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(campaign)
    await db.commit()


@router.get("/audience/count")
async def get_audience_count(
    segment_type: str,
    service_type: str | None = None,
    last_visit_months_start: int | None = None,
    last_visit_months_end: int | None = None,
    vehicle_type: str | None = None,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    from src.models.customer import Customer
    from src.models.job_card import JobCard
    from sqlalchemy import and_
    from datetime import timedelta

    if segment_type == "all_customers":
        q = select(func.count(Customer.id)).where(Customer.shop_id == shop_id)
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    if segment_type == "by_last_visit":
        if last_visit_months_start is None or last_visit_months_end is None:
            raise HTTPException(status_code=400, detail="last_visit_months_start and last_visit_months_end required")
        now = datetime.utcnow()
        window_start = now - timedelta(days=last_visit_months_end * 30)
        window_end = now - timedelta(days=last_visit_months_start * 30)
        subq = (
            select(JobCard.customer_id)
            .where(
                and_(
                    JobCard.shop_id == shop_id,
                    JobCard.created_at >= window_start,
                    JobCard.created_at <= window_end,
                )
            )
            .distinct()
        )
        q = select(func.count()).select_from(subq.subquery())
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    if segment_type == "by_service":
        if not service_type:
            raise HTTPException(status_code=400, detail="service_type required")
        # Count customers who have a job card with this service type in services JSON array
        subq = (
            select(JobCard.customer_id)
            .where(
                and_(
                    JobCard.shop_id == shop_id,
                    JobCard.services.cast(String).contains(service_type),
                )
            )
            .distinct()
        )
        q = select(func.count()).select_from(subq.subquery())
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    if segment_type == "by_vehicle_type":
        if not vehicle_type:
            raise HTTPException(status_code=400, detail="vehicle_type required")
        from src.models.vehicle import Vehicle
        subq = (
            select(JobCard.customer_id)
            .join(Vehicle, Vehicle.id == JobCard.vehicle_id)
            .where(
                and_(
                    JobCard.shop_id == shop_id,
                    Vehicle.make.ilike(f"%{vehicle_type}%"),
                )
            )
            .distinct()
        )
        q = select(func.count()).select_from(subq.subquery())
        result = await db.execute(q)
        return {"count": result.scalar() or 0}

    raise HTTPException(status_code=400, detail=f"Unknown segment_type: {segment_type}")


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Campaign).where(Campaign.id == uuid.UUID(campaign_id), Campaign.shop_id == shop_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status == "sent":
        raise HTTPException(status_code=400, detail="Campaign already sent")

    # Phase 1 stub — mark as sent, record send count from audience count
    campaign.status = "sent"
    campaign.sent_at = datetime.utcnow()
    campaign.stats = {**campaign.stats, "sent_count": 0, "note": "SMS/email delivery not yet wired"}
    await db.commit()
    await db.refresh(campaign)
    return _to_response(campaign)
```

- [ ] **Step 2: Register router in main.py**

In `backend/src/api/main.py`, add:

```python
from src.api.marketing import router as marketing_router
app.include_router(marketing_router)
```

- [ ] **Step 3: Run marketing tests**

```bash
cd backend
python -m pytest tests/test_api/test_marketing.py -v
```

Expected: 2 tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/src/api/marketing.py backend/src/api/main.py backend/tests/test_api/test_marketing.py
git commit -m "feat(marketing): add campaign CRUD, audience count, and send endpoints"
```

---

### Task 4: Frontend types + API functions

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`

- [ ] **Step 1: Add types to types.ts**

Append to `web/lib/types.ts`:

```typescript
// ── Diagnose ──────────────────────────────────────────────────────────────────

export interface DiagnosisItem {
  urgency?: number
  urgency_desc?: string
  desc: string
  layman_desc?: string
  part?: string
  repair?: { difficulty?: string }
}

export interface RepairPlanItem {
  repair_desc?: string
  desc?: string
  labor_hrs?: number
  labor_cost?: number
  confidence?: string
}

export interface TsbItem {
  tsb_id?: string
  title?: string
  component?: string
  pub_date?: string
  desc?: string
}

export interface RecallItem {
  recall_date?: string
  component?: string
  consequence?: string
  remedy?: string
  nhtsa_id?: string
}

export interface MaintenanceItem {
  desc?: string
  mileage?: number
  due_date?: string
}

export interface DiagnoseAnalyzeResult {
  diagnosis: DiagnosisItem[]
  repair_plan: RepairPlanItem[]
}

// ── Marketing ─────────────────────────────────────────────────────────────────

export interface Campaign {
  campaign_id: string
  shop_id: string
  name: string
  status: 'draft' | 'scheduled' | 'active' | 'sent'
  message_body: string
  channel: 'sms' | 'email' | 'both'
  audience_segment: AudienceSegment
  send_at: string | null
  sent_at: string | null
  stats: CampaignStats
  created_at: string
}

export interface AudienceSegment {
  type: 'all_customers' | 'by_service' | 'by_last_visit' | 'by_vehicle_type'
  service_type?: string
  last_visit_months_start?: number
  last_visit_months_end?: number
  vehicle_type?: string
}

export interface CampaignStats {
  sent_count?: number
  opened_count?: number
  booked_count?: number
  revenue_attributed?: number
}

export interface CampaignTemplate {
  id: string
  name: string
  message_body: string
}
```

- [ ] **Step 2: Add API functions to api.ts**

Append to `web/lib/api.ts`:

```typescript
// ── Diagnose ──────────────────────────────────────────────────────────────────

export interface AnalyzeRequest {
  year: number
  make: string
  model: string
  engine?: string
  mileage?: number
  dtcs: string[]
}

export const diagnoseAnalyze = async (req: AnalyzeRequest): Promise<DiagnoseAnalyzeResult> => {
  const { data } = await api.post('/diagnose/analyze', req)
  return data
}

export const diagnoseTsb = async (year: number, make: string, model: string, engine?: string): Promise<{ tsbs: TsbItem[] }> => {
  const { data } = await api.get('/diagnose/tsb', { params: { year, make, model, engine } })
  return data
}

export const diagnoseRecalls = async (year: number, make: string, model: string): Promise<{ recalls: RecallItem[] }> => {
  const { data } = await api.get('/diagnose/recalls', { params: { year, make, model } })
  return data
}

export const diagnoseMaintenance = async (year: number, make: string, model: string, mileage = 0): Promise<{ maintenance: MaintenanceItem[] }> => {
  const { data } = await api.get('/diagnose/maintenance', { params: { year, make, model, mileage } })
  return data
}

export const diagnoseAddToJobCard = async (jobCardId: string, diagnosis: DiagnosisItem[], repairPlan: RepairPlanItem[]): Promise<{ ok: boolean }> => {
  const { data } = await api.post('/diagnose/add-to-job-card', { job_card_id: jobCardId, diagnosis, repair_plan: repairPlan })
  return data
}

export const diagnoseSendSummary = async (customerId: string, diagnosis: DiagnosisItem[]): Promise<{ sms_text: string; sent: boolean }> => {
  const { data } = await api.post('/diagnose/send-summary', { customer_id: customerId, diagnosis })
  return data
}

// ── Marketing ─────────────────────────────────────────────────────────────────

export const fetchCampaignTemplates = async (): Promise<CampaignTemplate[]> => {
  const { data } = await api.get('/marketing/templates')
  return data
}

export const fetchCampaigns = async (status?: string): Promise<Campaign[]> => {
  const { data } = await api.get('/marketing/campaigns', { params: status ? { status } : undefined })
  return data
}

export const createCampaign = async (payload: Partial<Campaign>): Promise<Campaign> => {
  const { data } = await api.post('/marketing/campaigns', payload)
  return data
}

export const updateCampaign = async (id: string, payload: Partial<Campaign>): Promise<Campaign> => {
  const { data } = await api.put(`/marketing/campaigns/${id}`, payload)
  return data
}

export const deleteCampaign = async (id: string): Promise<void> => {
  await api.delete(`/marketing/campaigns/${id}`)
}

export const fetchAudienceCount = async (segment: AudienceSegment): Promise<number> => {
  const { data } = await api.get('/marketing/audience/count', {
    params: {
      segment_type: segment.type,
      service_type: segment.service_type,
      last_visit_months_start: segment.last_visit_months_start,
      last_visit_months_end: segment.last_visit_months_end,
      vehicle_type: segment.vehicle_type,
    },
  })
  return data.count
}

export const sendCampaign = async (id: string): Promise<Campaign> => {
  const { data } = await api.post(`/marketing/campaigns/${id}/send`)
  return data
}
```

- [ ] **Step 3: Commit**

```bash
git add web/lib/types.ts web/lib/api.ts
git commit -m "feat(diagnose,marketing): add frontend types and API functions"
```

---

### Task 5: Diagnose page

**Files:**
- Create: `web/components/diagnose/DiagnoseInputBar.tsx`
- Create: `web/components/diagnose/DiagnoseTabs.tsx`
- Create: `web/components/diagnose/DiagnoseActionPanel.tsx`
- Create: `web/app/diagnose/page.tsx`

- [ ] **Step 1: Create DiagnoseInputBar**

```tsx
// web/components/diagnose/DiagnoseInputBar.tsx
'use client'
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchCustomers } from '@/lib/api'

interface Props {
  onAnalyze: (params: { year: number; make: string; model: string; mileage: number; dtcs: string[] }) => void
  loading: boolean
}

export function DiagnoseInputBar({ onAnalyze, loading }: Props) {
  const [year, setYear] = useState('')
  const [make, setMake] = useState('')
  const [model, setModel] = useState('')
  const [mileage, setMileage] = useState('')
  const [dtcInput, setDtcInput] = useState('')
  const [dtcs, setDtcs] = useState<string[]>([])

  const addDtc = () => {
    const code = dtcInput.trim().toUpperCase()
    if (code && !dtcs.includes(code)) {
      setDtcs(prev => [...prev, code])
    }
    setDtcInput('')
  }

  const removeDtc = (code: string) => setDtcs(prev => prev.filter(d => d !== code))

  const handleAnalyze = () => {
    if (!year || !make || !model) return
    onAnalyze({ year: parseInt(year), make, model, mileage: parseInt(mileage) || 0, dtcs })
  }

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid #333',
    color: '#fff',
    borderRadius: '6px',
    padding: '8px 12px',
    fontSize: '14px',
    outline: 'none',
  }

  return (
    <div style={{ background: '#141414', border: '1px solid #222', borderRadius: '10px', padding: '20px', marginBottom: '24px' }}>
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
        <input
          placeholder="Year"
          value={year}
          onChange={e => setYear(e.target.value)}
          style={{ ...inputStyle, width: '80px' }}
          type="number"
        />
        <input
          placeholder="Make (e.g. Toyota)"
          value={make}
          onChange={e => setMake(e.target.value)}
          style={{ ...inputStyle, flex: 1, minWidth: '140px' }}
        />
        <input
          placeholder="Model (e.g. Camry)"
          value={model}
          onChange={e => setModel(e.target.value)}
          style={{ ...inputStyle, flex: 1, minWidth: '140px' }}
        />
        <input
          placeholder="Mileage"
          value={mileage}
          onChange={e => setMileage(e.target.value)}
          style={{ ...inputStyle, width: '120px' }}
          type="number"
        />
      </div>

      <div style={{ display: 'flex', gap: '8px', marginBottom: dtcs.length ? '12px' : '0', flexWrap: 'wrap' }}>
        <input
          placeholder="DTC code (e.g. P0300)"
          value={dtcInput}
          onChange={e => setDtcInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && addDtc()}
          style={{ ...inputStyle, flex: 1, minWidth: '200px' }}
        />
        <button onClick={addDtc} style={{ background: '#222', border: '1px solid #333', color: '#aaa', borderRadius: '6px', padding: '8px 16px', cursor: 'pointer', fontSize: '14px' }}>
          + Add Code
        </button>
        <button
          onClick={handleAnalyze}
          disabled={loading || !year || !make || !model}
          style={{
            background: loading ? '#333' : '#d97706',
            color: '#000',
            border: 'none',
            borderRadius: '6px',
            padding: '8px 24px',
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: '14px',
          }}
        >
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </div>

      {dtcs.length > 0 && (
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {dtcs.map(code => (
            <span
              key={code}
              style={{ background: '#1f2937', color: '#fbbf24', border: '1px solid #374151', borderRadius: '20px', padding: '4px 12px', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              {code}
              <button onClick={() => removeDtc(code)} style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '14px', lineHeight: 1 }}>×</button>
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create DiagnoseActionPanel**

```tsx
// web/components/diagnose/DiagnoseActionPanel.tsx
'use client'
import { DiagnosisItem, RepairPlanItem } from '@/lib/types'
import { diagnoseAddToJobCard, diagnoseSendSummary } from '@/lib/api'
import { useState } from 'react'

interface Props {
  diagnosis: DiagnosisItem[]
  repairPlan: RepairPlanItem[]
  jobCardId: string | null
  customerId: string | null
}

export function DiagnoseActionPanel({ diagnosis, repairPlan, jobCardId, customerId }: Props) {
  const [addedToCard, setAddedToCard] = useState(false)
  const [smsSent, setSmsSent] = useState(false)
  const [smsPreview, setSmsPreview] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)

  const partsNeeded = repairPlan
    .filter(r => r.repair_desc || r.desc)
    .slice(0, 5)

  const totalLaborHrs = repairPlan.reduce((sum, r) => sum + (r.labor_hrs || 0), 0)

  const handleAddToJobCard = async () => {
    if (!jobCardId) return
    setAdding(true)
    await diagnoseAddToJobCard(jobCardId, diagnosis, repairPlan)
    setAddedToCard(true)
    setAdding(false)
  }

  const handleSendSummary = async () => {
    if (!customerId) return
    const result = await diagnoseSendSummary(customerId, diagnosis)
    setSmsPreview(result.sms_text)
    setSmsSent(true)
  }

  const sectionStyle = { marginBottom: '20px' }
  const labelStyle = { color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '0.05em', marginBottom: '8px' }
  const cardStyle = { background: '#1a1a1a', border: '1px solid #2a2a2a', borderRadius: '6px', padding: '10px 12px', marginBottom: '6px', fontSize: '13px', color: '#e5e7eb' }

  return (
    <div style={{ width: '280px', flexShrink: 0, borderLeft: '1px solid #222', paddingLeft: '24px' }}>
      <div style={sectionStyle}>
        <div style={labelStyle}>Parts Needed</div>
        {partsNeeded.length === 0 ? (
          <div style={{ color: '#4b5563', fontSize: '13px' }}>No parts identified yet</div>
        ) : (
          partsNeeded.map((r, i) => (
            <div key={i} style={cardStyle}>{r.repair_desc || r.desc}</div>
          ))
        )}
      </div>

      <div style={sectionStyle}>
        <div style={labelStyle}>Labor Estimate</div>
        <div style={{ ...cardStyle, color: '#d97706', fontWeight: 600 }}>
          {totalLaborHrs > 0 ? `${totalLaborHrs.toFixed(1)} hrs` : '—'}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column' as const, gap: '10px' }}>
        <button
          onClick={handleAddToJobCard}
          disabled={!jobCardId || addedToCard || adding}
          style={{
            background: addedToCard ? '#14532d' : '#d97706',
            color: addedToCard ? '#86efac' : '#000',
            border: 'none',
            borderRadius: '6px',
            padding: '10px 14px',
            cursor: !jobCardId || addedToCard ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: '13px',
            opacity: !jobCardId ? 0.4 : 1,
          }}
        >
          {addedToCard ? '✓ Added to Job Card' : adding ? 'Adding…' : '+ Add to Job Card'}
        </button>

        <button
          onClick={handleSendSummary}
          disabled={!customerId || smsSent}
          style={{
            background: smsSent ? '#1e3a5f' : '#1a1a1a',
            color: smsSent ? '#93c5fd' : '#e5e7eb',
            border: '1px solid #333',
            borderRadius: '6px',
            padding: '10px 14px',
            cursor: !customerId || smsSent ? 'not-allowed' : 'pointer',
            fontSize: '13px',
            opacity: !customerId ? 0.4 : 1,
          }}
        >
          {smsSent ? '✓ Summary Sent' : 'Send Summary to Customer'}
        </button>

        {smsPreview && (
          <div style={{ background: '#111', border: '1px solid #1d4ed8', borderRadius: '6px', padding: '10px', fontSize: '12px', color: '#93c5fd', lineHeight: 1.5 }}>
            <div style={{ color: '#6b7280', fontSize: '10px', marginBottom: '4px' }}>PREVIEW</div>
            {smsPreview}
          </div>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create DiagnoseTabs**

```tsx
// web/components/diagnose/DiagnoseTabs.tsx
'use client'
import { DiagnosisItem, RepairPlanItem, TsbItem, RecallItem, MaintenanceItem } from '@/lib/types'

type Tab = 'diagnosis' | 'repair' | 'tsb' | 'recalls' | 'maintenance'

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
  diagnosis: DiagnosisItem[]
  repairPlan: RepairPlanItem[]
  tsbs: TsbItem[]
  recalls: RecallItem[]
  maintenance: MaintenanceItem[]
  loading: boolean
}

const TABS: { key: Tab; label: string }[] = [
  { key: 'diagnosis', label: 'Diagnosis' },
  { key: 'repair', label: 'Repair Plan' },
  { key: 'tsb', label: 'TSB' },
  { key: 'recalls', label: 'Recalls' },
  { key: 'maintenance', label: 'Maintenance' },
]

export function DiagnoseTabs({ activeTab, onTabChange, diagnosis, repairPlan, tsbs, recalls, maintenance, loading }: Props) {
  const tabBar = (
    <div style={{ display: 'flex', borderBottom: '1px solid #222', marginBottom: '20px' }}>
      {TABS.map(tab => (
        <button
          key={tab.key}
          onClick={() => onTabChange(tab.key)}
          style={{
            background: 'none',
            border: 'none',
            color: activeTab === tab.key ? '#d97706' : '#6b7280',
            borderBottom: activeTab === tab.key ? '2px solid #d97706' : '2px solid transparent',
            padding: '10px 16px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: activeTab === tab.key ? 600 : 400,
            marginBottom: '-1px',
          }}
        >
          {tab.label}
        </button>
      ))}
    </div>
  )

  const itemCard = (children: React.ReactNode, key: string | number) => (
    <div key={key} style={{ background: '#141414', border: '1px solid #222', borderRadius: '8px', padding: '14px 16px', marginBottom: '10px' }}>
      {children}
    </div>
  )

  const pill = (text: string, color = '#374151') => (
    <span style={{ background: color, color: '#e5e7eb', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', fontWeight: 600 }}>{text}</span>
  )

  if (loading) {
    return (
      <div style={{ flex: 1 }}>
        {tabBar}
        <div style={{ color: '#6b7280', fontSize: '14px', paddingTop: '20px' }}>Analyzing…</div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1 }}>
      {tabBar}

      {activeTab === 'diagnosis' && (
        diagnosis.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>Run an analysis to see diagnostic results.</div>
          : diagnosis.map((d, i) => itemCard(
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px' }}>{d.layman_desc || d.desc}</div>
                {d.urgency_desc && pill(d.urgency_desc, d.urgency === 1 ? '#7f1d1d' : d.urgency === 2 ? '#78350f' : '#1e3a5f')}
              </div>
              {d.layman_desc && d.desc !== d.layman_desc && (
                <div style={{ color: '#6b7280', fontSize: '12px', marginBottom: '4px' }}>{d.desc}</div>
              )}
              {d.part && <div style={{ color: '#d97706', fontSize: '12px' }}>Part: {d.part}</div>}
            </>,
            i
          ))
      )}

      {activeTab === 'repair' && (
        repairPlan.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No repair plan data yet.</div>
          : repairPlan.map((r, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{r.repair_desc || r.desc}</div>
              <div style={{ display: 'flex', gap: '12px', fontSize: '12px', color: '#9ca3af' }}>
                {r.labor_hrs != null && <span>Labor: {r.labor_hrs}h</span>}
                {r.confidence && <span>Confidence: {r.confidence}</span>}
              </div>
            </>,
            i
          ))
      )}

      {activeTab === 'tsb' && (
        tsbs.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No TSBs found for this vehicle.</div>
          : tsbs.map((t, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{t.title || 'TSB'}</div>
              {t.component && <div style={{ color: '#9ca3af', fontSize: '12px', marginBottom: '4px' }}>Component: {t.component}</div>}
              {t.desc && <div style={{ color: '#6b7280', fontSize: '12px' }}>{t.desc}</div>}
            </>,
            i
          ))
      )}

      {activeTab === 'recalls' && (
        recalls.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No open recalls found.</div>
          : recalls.map((r, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{r.component || 'Recall'}</div>
              {r.consequence && <div style={{ color: '#fca5a5', fontSize: '12px', marginBottom: '4px' }}>Risk: {r.consequence}</div>}
              {r.remedy && <div style={{ color: '#9ca3af', fontSize: '12px', marginBottom: '4px' }}>Remedy: {r.remedy}</div>}
              {r.nhtsa_id && <div style={{ color: '#6b7280', fontSize: '11px' }}>NHTSA: {r.nhtsa_id}</div>}
            </>,
            i
          ))
      )}

      {activeTab === 'maintenance' && (
        maintenance.length === 0
          ? <div style={{ color: '#4b5563', fontSize: '14px' }}>No maintenance data available.</div>
          : maintenance.map((m, i) => itemCard(
            <>
              <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{m.desc || 'Maintenance'}</div>
              {m.mileage != null && <div style={{ color: '#d97706', fontSize: '12px' }}>Due at: {m.mileage.toLocaleString()} mi</div>}
            </>,
            i
          ))
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create Diagnose page**

```tsx
// web/app/diagnose/page.tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { DiagnoseInputBar } from '@/components/diagnose/DiagnoseInputBar'
import { DiagnoseTabs } from '@/components/diagnose/DiagnoseTabs'
import { DiagnoseActionPanel } from '@/components/diagnose/DiagnoseActionPanel'
import {
  diagnoseAnalyze,
  diagnoseTsb,
  diagnoseRecalls,
  diagnoseMaintenance,
} from '@/lib/api'
import type { DiagnosisItem, RepairPlanItem, TsbItem, RecallItem, MaintenanceItem } from '@/lib/types'

type Tab = 'diagnosis' | 'repair' | 'tsb' | 'recalls' | 'maintenance'

interface VehicleContext {
  year: number
  make: string
  model: string
  mileage: number
  dtcs: string[]
}

export default function DiagnosePage() {
  const [activeTab, setActiveTab] = useState<Tab>('diagnosis')
  const [vehicleCtx, setVehicleCtx] = useState<VehicleContext | null>(null)
  const [diagnosis, setDiagnosis] = useState<DiagnosisItem[]>([])
  const [repairPlan, setRepairPlan] = useState<RepairPlanItem[]>([])
  const [tsbs, setTsbs] = useState<TsbItem[]>([])
  const [recalls, setRecalls] = useState<RecallItem[]>([])
  const [maintenance, setMaintenance] = useState<MaintenanceItem[]>([])
  const [analyzing, setAnalyzing] = useState(false)

  const hasOpenRecall = recalls.some(() => true)

  const handleAnalyze = async (params: VehicleContext) => {
    setVehicleCtx(params)
    setAnalyzing(true)
    try {
      const [analyzeResult, tsbResult, recallResult, maintenanceResult] = await Promise.all([
        diagnoseAnalyze(params),
        diagnoseTsb(params.year, params.make, params.model),
        diagnoseRecalls(params.year, params.make, params.model),
        diagnoseMaintenance(params.year, params.make, params.model, params.mileage),
      ])
      setDiagnosis(analyzeResult.diagnosis)
      setRepairPlan(analyzeResult.repair_plan)
      setTsbs(tsbResult.tsbs)
      setRecalls(recallResult.recalls)
      setMaintenance(maintenanceResult.maintenance)
    } catch (_) {
      // partial results ok; data already set before error
    } finally {
      setAnalyzing(false)
    }
  }

  return (
    <div style={{ background: '#0d0d0d', minHeight: '100vh', padding: '32px', color: '#fff', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#f9fafb', marginBottom: '8px' }}>Diagnose</h1>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>Vehicle diagnostic lookup powered by CarMD</p>

      <DiagnoseInputBar onAnalyze={handleAnalyze} loading={analyzing} />

      {hasOpenRecall && (
        <div style={{ background: '#450a0a', border: '1px solid #7f1d1d', borderRadius: '8px', padding: '12px 16px', marginBottom: '20px', color: '#fca5a5', fontWeight: 600, fontSize: '14px' }}>
          ⚠ Open NHTSA Safety Recall — See Recalls tab for details
        </div>
      )}

      <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-start' }}>
        <DiagnoseTabs
          activeTab={activeTab}
          onTabChange={setActiveTab}
          diagnosis={diagnosis}
          repairPlan={repairPlan}
          tsbs={tsbs}
          recalls={recalls}
          maintenance={maintenance}
          loading={analyzing}
        />
        <DiagnoseActionPanel
          diagnosis={diagnosis}
          repairPlan={repairPlan}
          jobCardId={null}
          customerId={null}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Commit**

```bash
git add web/app/diagnose/ web/components/diagnose/
git commit -m "feat(diagnose): add Diagnose page with CarMD result tabs and action panel"
```

---

### Task 6: Marketing page + Dashboard tiles

**Files:**
- Create: `web/components/marketing/CampaignList.tsx`
- Create: `web/components/marketing/ComposePanel.tsx`
- Create: `web/components/marketing/AudienceSelector.tsx`
- Create: `web/app/marketing/page.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Create AudienceSelector**

```tsx
// web/components/marketing/AudienceSelector.tsx
'use client'
import { useEffect, useState } from 'react'
import { fetchAudienceCount } from '@/lib/api'
import type { AudienceSegment } from '@/lib/types'

interface Props {
  value: AudienceSegment
  onChange: (seg: AudienceSegment) => void
}

const SEGMENT_OPTIONS: { type: AudienceSegment['type']; label: string }[] = [
  { type: 'all_customers', label: 'All Customers' },
  { type: 'by_service', label: 'By Service History' },
  { type: 'by_last_visit', label: 'By Last Visit Window' },
  { type: 'by_vehicle_type', label: 'By Vehicle Type' },
]

const SERVICE_TYPES = ['Oil Change', 'Tire Rotation', 'AC Check', 'Full Service', 'Brakes', 'Alignment']

export function AudienceSelector({ value, onChange }: Props) {
  const [count, setCount] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetchAudienceCount(value)
      .then(c => { if (!cancelled) setCount(c) })
      .catch(() => { if (!cancelled) setCount(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [JSON.stringify(value)])

  const inputStyle = {
    background: '#1a1a1a',
    border: '1px solid #333',
    color: '#fff',
    borderRadius: '6px',
    padding: '7px 10px',
    fontSize: '13px',
    width: '100%',
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <div style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Audience</div>
        <div style={{ color: loading ? '#6b7280' : '#d97706', fontSize: '13px', fontWeight: 600 }}>
          {loading ? '…' : count != null ? `${count} contacts` : '—'}
        </div>
      </div>

      <select
        value={value.type}
        onChange={e => onChange({ type: e.target.value as AudienceSegment['type'] })}
        style={{ ...inputStyle, marginBottom: '10px' }}
      >
        {SEGMENT_OPTIONS.map(o => (
          <option key={o.type} value={o.type}>{o.label}</option>
        ))}
      </select>

      {value.type === 'by_service' && (
        <select
          value={value.service_type || ''}
          onChange={e => onChange({ ...value, service_type: e.target.value })}
          style={inputStyle}
        >
          <option value="">Select service type…</option>
          {SERVICE_TYPES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      )}

      {value.type === 'by_last_visit' && (
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input
            type="number"
            placeholder="From (months)"
            value={value.last_visit_months_start || ''}
            onChange={e => onChange({ ...value, last_visit_months_start: parseInt(e.target.value) || undefined })}
            style={{ ...inputStyle, flex: 1 }}
          />
          <span style={{ color: '#6b7280' }}>–</span>
          <input
            type="number"
            placeholder="To (months)"
            value={value.last_visit_months_end || ''}
            onChange={e => onChange({ ...value, last_visit_months_end: parseInt(e.target.value) || undefined })}
            style={{ ...inputStyle, flex: 1 }}
          />
        </div>
      )}

      {value.type === 'by_vehicle_type' && (
        <input
          placeholder="Vehicle make (e.g. Toyota)"
          value={value.vehicle_type || ''}
          onChange={e => onChange({ ...value, vehicle_type: e.target.value })}
          style={inputStyle}
        />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Create ComposePanel**

```tsx
// web/components/marketing/ComposePanel.tsx
'use client'
import { useState } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { createCampaign, updateCampaign, sendCampaign, fetchCampaignTemplates } from '@/lib/api'
import { AudienceSelector } from './AudienceSelector'
import type { Campaign, AudienceSegment } from '@/lib/types'

interface Props {
  campaign: Campaign | null
  onClose: () => void
}

const TEMPLATE_VARS = ['{first_name}', '{vehicle}', '{service}', '{booking_link}']

export function ComposePanel({ campaign, onClose }: Props) {
  const qc = useQueryClient()
  const isNew = !campaign

  const [name, setName] = useState(campaign?.name || '')
  const [body, setBody] = useState(campaign?.message_body || '')
  const [channel, setChannel] = useState<'sms' | 'email' | 'both'>(campaign?.channel || 'sms')
  const [segment, setSegment] = useState<AudienceSegment>(campaign?.audience_segment || { type: 'all_customers' })
  const [selectedTemplate, setSelectedTemplate] = useState('')

  const { data: templates = [] } = useQuery({ queryKey: ['campaign-templates'], queryFn: fetchCampaignTemplates })

  const save = useMutation({
    mutationFn: () => {
      const payload = { name, message_body: body, channel, audience_segment: segment }
      return isNew ? createCampaign(payload) : updateCampaign(campaign!.campaign_id, payload)
    },
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); onClose() },
  })

  const send = useMutation({
    mutationFn: () => sendCampaign(campaign!.campaign_id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['campaigns'] }); onClose() },
  })

  const applyTemplate = (templateId: string) => {
    const t = templates.find(t => t.id === templateId)
    if (t) setBody(t.message_body)
  }

  const insertVar = (v: string) => setBody(prev => prev + v)

  const inputStyle = { background: '#1a1a1a', border: '1px solid #333', color: '#fff', borderRadius: '6px', padding: '8px 12px', fontSize: '14px', width: '100%', outline: 'none' }
  const labelStyle = { color: '#9ca3af', fontSize: '12px', fontWeight: 600 as const, textTransform: 'uppercase' as const, letterSpacing: '0.05em', display: 'block', marginBottom: '6px' }

  return (
    <div style={{ width: '360px', background: '#111', border: '1px solid #222', borderRadius: '10px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>{isNew ? 'New Campaign' : 'Edit Campaign'}</h2>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#6b7280', cursor: 'pointer', fontSize: '18px' }}>×</button>
      </div>

      <div>
        <label style={labelStyle}>Campaign Name</label>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="e.g. Summer AC Promo" style={inputStyle} />
      </div>

      <div>
        <label style={labelStyle}>Template</label>
        <select value={selectedTemplate} onChange={e => { setSelectedTemplate(e.target.value); applyTemplate(e.target.value) }} style={{ ...inputStyle, cursor: 'pointer' }}>
          <option value="">Use a template…</option>
          {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      </div>

      <div>
        <label style={labelStyle}>Message</label>
        <textarea
          value={body}
          onChange={e => setBody(e.target.value)}
          rows={4}
          placeholder="Hi {first_name}, …"
          style={{ ...inputStyle, resize: 'vertical' as const, fontFamily: 'inherit' }}
        />
        <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
          {TEMPLATE_VARS.map(v => (
            <button key={v} onClick={() => insertVar(v)} style={{ background: '#1f2937', border: '1px solid #374151', color: '#93c5fd', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', cursor: 'pointer' }}>
              {v}
            </button>
          ))}
        </div>
      </div>

      <AudienceSelector value={segment} onChange={setSegment} />

      <div>
        <label style={labelStyle}>Channel</label>
        <div style={{ display: 'flex', gap: '8px' }}>
          {(['sms', 'email', 'both'] as const).map(ch => (
            <button
              key={ch}
              onClick={() => setChannel(ch)}
              style={{
                flex: 1,
                background: channel === ch ? '#d97706' : '#1a1a1a',
                color: channel === ch ? '#000' : '#9ca3af',
                border: `1px solid ${channel === ch ? '#d97706' : '#333'}`,
                borderRadius: '6px',
                padding: '8px',
                cursor: 'pointer',
                fontSize: '13px',
                fontWeight: channel === ch ? 600 : 400,
                textTransform: 'capitalize',
              }}
            >
              {ch}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending || !name || !body}
          style={{ flex: 1, background: '#1a1a1a', color: '#e5e7eb', border: '1px solid #333', borderRadius: '6px', padding: '10px', cursor: 'pointer', fontSize: '14px' }}
        >
          {save.isPending ? 'Saving…' : 'Save Draft'}
        </button>
        {!isNew && campaign?.status !== 'sent' && (
          <button
            onClick={() => send.mutate()}
            disabled={send.isPending}
            style={{ flex: 1, background: '#d97706', color: '#000', border: 'none', borderRadius: '6px', padding: '10px', cursor: 'pointer', fontWeight: 700, fontSize: '14px' }}
          >
            {send.isPending ? 'Sending…' : 'Send Now'}
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Create CampaignList**

```tsx
// web/components/marketing/CampaignList.tsx
'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchCampaigns, deleteCampaign } from '@/lib/api'
import type { Campaign } from '@/lib/types'

interface Props {
  selectedId: string | null
  onSelect: (c: Campaign) => void
  onNew: () => void
}

const STATUS_COLORS: Record<string, string> = {
  draft: '#374151',
  scheduled: '#1e3a5f',
  active: '#14532d',
  sent: '#1f2937',
}

const STATUS_TEXT: Record<string, string> = {
  draft: '#9ca3af',
  scheduled: '#93c5fd',
  active: '#86efac',
  sent: '#6b7280',
}

export function CampaignList({ selectedId, onSelect, onNew }: Props) {
  const qc = useQueryClient()
  const { data: campaigns = [], isLoading } = useQuery({ queryKey: ['campaigns'], queryFn: () => fetchCampaigns() })

  const del = useMutation({
    mutationFn: deleteCampaign,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['campaigns'] }),
  })

  return (
    <div style={{ flex: 1 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h2 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#f9fafb' }}>Campaigns</h2>
        <button
          onClick={onNew}
          style={{ background: '#d97706', color: '#000', border: 'none', borderRadius: '6px', padding: '7px 16px', cursor: 'pointer', fontWeight: 600, fontSize: '13px' }}
        >
          + New Campaign
        </button>
      </div>

      {isLoading ? (
        <div style={{ color: '#6b7280', fontSize: '14px' }}>Loading…</div>
      ) : campaigns.length === 0 ? (
        <div style={{ background: '#111', border: '1px solid #222', borderRadius: '8px', padding: '40px', textAlign: 'center', color: '#4b5563' }}>
          No campaigns yet. Create your first one.
        </div>
      ) : (
        campaigns.map(c => (
          <div
            key={c.campaign_id}
            onClick={() => onSelect(c)}
            style={{
              background: selectedId === c.campaign_id ? '#1a1a1a' : '#111',
              border: `1px solid ${selectedId === c.campaign_id ? '#d97706' : '#222'}`,
              borderRadius: '8px',
              padding: '14px 16px',
              marginBottom: '8px',
              cursor: 'pointer',
              transition: 'border-color 0.1s',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: '14px', marginBottom: '4px' }}>{c.name}</div>
                <div style={{ color: '#6b7280', fontSize: '12px', marginBottom: '6px' }}>
                  {c.channel.toUpperCase()} · {new Date(c.created_at).toLocaleDateString()}
                </div>
                {c.stats.sent_count != null && (
                  <div style={{ color: '#6b7280', fontSize: '12px' }}>
                    Sent: {c.stats.sent_count} · Opened: {c.stats.opened_count || 0} · Booked: {c.stats.booked_count || 0}
                  </div>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '8px' }}>
                <span style={{ background: STATUS_COLORS[c.status] || '#1f2937', color: STATUS_TEXT[c.status] || '#9ca3af', borderRadius: '12px', padding: '2px 10px', fontSize: '11px', fontWeight: 600 }}>
                  {c.status}
                </span>
                {c.status === 'draft' && (
                  <button
                    onClick={e => { e.stopPropagation(); del.mutate(c.campaign_id) }}
                    style={{ background: 'none', border: 'none', color: '#4b5563', cursor: 'pointer', fontSize: '12px' }}
                  >
                    Delete
                  </button>
                )}
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create Marketing page**

```tsx
// web/app/marketing/page.tsx
'use client'
import { useState } from 'react'
import { CampaignList } from '@/components/marketing/CampaignList'
import { ComposePanel } from '@/components/marketing/ComposePanel'
import type { Campaign } from '@/lib/types'

export default function MarketingPage() {
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)
  const [composing, setComposing] = useState(false)

  const handleNew = () => {
    setSelectedCampaign(null)
    setComposing(true)
  }

  const handleSelect = (c: Campaign) => {
    setSelectedCampaign(c)
    setComposing(true)
  }

  const handleClose = () => {
    setComposing(false)
    setSelectedCampaign(null)
  }

  return (
    <div style={{ background: '#0d0d0d', minHeight: '100vh', padding: '32px', color: '#fff', fontFamily: 'system-ui, sans-serif' }}>
      <h1 style={{ fontSize: '22px', fontWeight: 700, color: '#f9fafb', marginBottom: '4px' }}>Marketing</h1>
      <p style={{ color: '#6b7280', fontSize: '14px', marginBottom: '24px' }}>SMS & email campaigns for your customers</p>

      <div style={{ display: 'flex', gap: '32px', alignItems: 'flex-start' }}>
        <CampaignList
          selectedId={selectedCampaign?.campaign_id ?? null}
          onSelect={handleSelect}
          onNew={handleNew}
        />
        {composing && (
          <ComposePanel
            campaign={selectedCampaign}
            onClose={handleClose}
          />
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Add Diagnose + Marketing tiles to Dashboard**

Read `web/app/page.tsx` first, then find the dashboard tile section and add two new tiles. The existing tile pattern (from the dashboard component) likely looks like:

```tsx
// Add these two tiles to the existing dashboard tiles array/section in web/app/page.tsx.
// Find the place where other tiles like Customers, Reports, etc. are rendered and add:

{
  label: 'Diagnose',
  description: 'CarMD vehicle diagnostic lookup',
  href: '/diagnose',
  icon: '🔍',
},
{
  label: 'Marketing',
  description: 'SMS & email campaign manager',
  href: '/marketing',
  icon: '📣',
},
```

Read the actual file first to match the existing tile format exactly, then add the tiles using the same structure.

- [ ] **Step 6: Commit**

```bash
git add web/app/marketing/ web/components/marketing/ web/app/diagnose/ web/components/diagnose/ web/app/page.tsx
git commit -m "feat(marketing): add Marketing page with campaign manager and compose panel"
```

---

## Self-Review Checklist

After implementation, verify against the spec:

**Feature 10 (Diagnose):**
- [ ] Input bar: year/make/model/engine/mileage + DTC pills + Analyze button ✓
- [ ] Recall banner visible when open recall exists ✓
- [ ] 5 result tabs: Diagnosis, Repair Plan, TSB, Recalls, Maintenance ✓
- [ ] Right action panel: parts needed, labor estimate, add to job card, send summary ✓
- [ ] Backend proxies to 5 CarMD endpoints ✓
- [ ] 422 when CarMD credentials not configured ✓

**Feature 12 (Marketing):**
- [ ] Campaign states: draft → scheduled → active → sent ✓
- [ ] 4 audience segment types with live count ✓
- [ ] Compose panel: name, message, templates, variable insertion, channel toggles ✓
- [ ] Campaign list with status badges and stats ✓
- [ ] Pre-built templates endpoint ✓
- [ ] Send stub marks campaign as sent ✓

**Both:**
- [ ] Dashboard tiles added ✓
- [ ] All CarMD credentials stored in ShopSettings (carmd_api_key, carmd_partner_token) ✓
- [ ] Alembic migrations for both ShopSettings columns and campaigns table ✓
