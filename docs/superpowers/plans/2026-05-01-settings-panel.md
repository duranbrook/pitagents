# Settings Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the avatar dropdown with a slide-in settings panel covering 7 sections (Account, Shop Profile, Appearance, Booking, Notifications, Integrations, Agents & AI).

**Architecture:** Backend gets DB-backed auth (replacing in-memory dict) plus 4 new endpoints. Frontend gets a fixed-position `SettingsPanel` component mounted in `AppShell` alongside 7 section components. Existing `SettingsDropdown` and `/settings` page are deleted; `AppearanceTab` and `AgentsTab` are migrated into the panel.

**Tech Stack:** Next.js App Router, React, TanStack Query v5, FastAPI, SQLAlchemy async, passlib, pytest with TestClient

---

## File Map

### Backend — modified
- `backend/src/api/auth.py` — switch login to DB query; add GET /auth/me, PATCH /auth/profile, PATCH /auth/password
- `backend/src/api/appointments.py` — add GET/PATCH /appointments/my-config (owner-facing booking config)
- `backend/src/api/shop_settings.py` — add GET/PATCH /settings/profile (Shop model fields); expand ShopSettingsResponse

### Backend — modified tests
- `backend/tests/test_api/test_auth.py` — rewrite to use conftest `client` + mock_db; add tests for new endpoints
- `backend/tests/test_api/test_appointments.py` — add /my-config tests
- `backend/tests/test_api/test_shop_settings.py` — add /profile tests

### Frontend — new
- `web/components/settings/SettingsPanel.tsx` — slide-in shell with sidebar nav
- `web/components/settings/sections/AccountSection.tsx`
- `web/components/settings/sections/ShopProfileSection.tsx`
- `web/components/settings/sections/AppearanceSection.tsx`
- `web/components/settings/sections/BookingSection.tsx`
- `web/components/settings/sections/NotificationsSection.tsx`
- `web/components/settings/sections/IntegrationsSection.tsx`
- `web/components/settings/sections/AgentsSection.tsx`

### Frontend — modified
- `web/components/AppShell.tsx` — remove dropdown, mount SettingsPanel
- `web/lib/types.ts` — add UserProfile, ShopProfile; expand ShopSettings
- `web/lib/api.ts` — add getMe, updateProfile, updatePassword, getMyBookingConfig, updateMyBookingConfig, getShopProfile, updateShopProfile

### Frontend — deleted
- `web/components/SettingsDropdown.tsx`
- `web/app/settings/page.tsx` → replaced with `redirect('/')`

---

### Task 1: DB-backed auth + /auth/me + /auth/profile + /auth/password

**Files:**
- Modify: `backend/src/api/auth.py`
- Modify: `backend/tests/test_api/test_auth.py`

Context: `auth.py` currently uses `_TEST_USERS` in-memory dict. The `users` table already exists in Postgres with columns `id`, `shop_id`, `email`, `hashed_password`, `role`, `name`. The conftest at `backend/tests/conftest.py` provides `client`, `mock_db`, `auth_headers` fixtures — use these instead of creating a new client fixture. The conftest `mock_db` is an `AsyncMock` with `execute.return_value.scalar_one_or_none.return_value = None` by default.

- [ ] **Step 1: Write failing tests**

Replace the entire contents of `backend/tests/test_api/test_auth.py` with:

```python
import os
import uuid
import pytest
from unittest.mock import MagicMock
from passlib.context import CryptContext

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_autoshop")
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_user(email="owner@shop.com", password="testpass", role="owner", name="Test Owner"):
    u = MagicMock()
    u.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    u.shop_id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    u.email = email
    u.role = role
    u.name = name
    u.hashed_password = pwd_ctx.hash(password)
    return u


def test_login_returns_token(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.post("/auth/login", json={"email": "owner@shop.com", "password": "testpass"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.post("/auth/login", json={"email": "owner@shop.com", "password": "wrongpassword"})
    assert resp.status_code == 401


def test_login_unknown_email_returns_401(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.post("/auth/login", json={"email": "nobody@shop.com", "password": "testpass"})
    assert resp.status_code == 401


def test_login_token_contains_shop_id(client, mock_db):
    import jwt as pyjwt
    from src.config import settings
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.post("/auth/login", json={"email": "owner@shop.com", "password": "testpass"})
    assert resp.status_code == 200
    payload = pyjwt.decode(
        resp.json()["access_token"],
        settings.JWT_SECRET.get_secret_value(),
        algorithms=[settings.JWT_ALGORITHM],
    )
    assert payload.get("shop_id") == "00000000-0000-0000-0000-000000000099"


def test_get_me(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "owner@shop.com"
    assert data["name"] == "Test Owner"
    assert data["role"] == "owner"


def test_update_profile(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.patch("/auth/profile", json={"name": "New Name"}, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "owner@shop.com"


def test_change_password_success(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.patch(
        "/auth/password",
        json={"current_password": "testpass", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_change_password_wrong_current_returns_400(client, mock_db, auth_headers):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user()
    resp = client.patch(
        "/auth/password",
        json={"current_password": "wrongpass", "new_password": "newpass123"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "incorrect" in resp.json()["detail"].lower()


def test_technician_cannot_access_owner_route(client, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = _make_user(role="technician")
    login_resp = client.post("/auth/login", json={"email": "tech@shop.com", "password": "testpass"})
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    resp = client.get("/reports", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/test_auth.py -v 2>&1 | tail -20
```

Expected: multiple failures — `test_login_returns_token` fails because `login` doesn't use DB yet; `test_get_me` fails with 404/422 because `/auth/me` doesn't exist.

- [ ] **Step 3: Rewrite auth.py**

Replace the entire contents of `backend/src/api/auth.py` with:

```python
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.config import settings
from src.db.base import get_db
from src.models.user import User
from src.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    name: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    role: str


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if user is None or not pwd_ctx.verify(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({
        "sub": str(user.id),
        "shop_id": str(user.shop_id),
        "role": user.role,
        "email": user.email,
    })
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfileResponse(id=str(user.id), email=user.email, name=user.name, role=user.role)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    body: ProfileUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.name = body.name
    await db.commit()
    await db.refresh(user)
    return UserProfileResponse(id=str(user.id), email=user.email, name=user.name, role=user.role)


@router.patch("/password")
async def change_password(
    body: PasswordChange,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == uuid.UUID(current_user["sub"])))
    user = result.scalar_one_or_none()
    if user is None or not pwd_ctx.verify(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    user.hashed_password = pwd_ctx.hash(body.new_password)
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/test_auth.py -v 2>&1 | tail -20
```

Expected: all 9 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add backend/src/api/auth.py backend/tests/test_api/test_auth.py
git commit -m "feat(auth): switch to DB-backed login; add /me, /profile, /password endpoints"
```

---

### Task 2: /appointments/my-config endpoints

**Files:**
- Modify: `backend/src/api/appointments.py`
- Modify: `backend/tests/test_api/test_appointments.py`

Context: `appointments.py` has `router` with prefix `/appointments`. The `BookingConfig` model has fields `slug`, `working_hours_start`, `working_hours_end`, `slot_duration_minutes`, `shop_id`. The `_cfg_to_response` helper already exists. The new routes must be added **before** any `/{appt_id}` route to avoid FastAPI treating "my-config" as an appointment ID. The conftest `auth_headers` fixture sets `shop_id = "00000000-0000-0000-0000-000000000099"` in the JWT.

- [ ] **Step 1: Write failing tests**

Add these tests to the END of `backend/tests/test_api/test_appointments.py`:

```python
def test_get_my_booking_config(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    cfg = MagicMock()
    cfg.slug = "test-shop"
    cfg.working_hours_start = "08:00"
    cfg.working_hours_end = "17:00"
    cfg.slot_duration_minutes = "60"
    mock_db.execute.return_value.scalar_one_or_none.return_value = cfg
    resp = client.get("/appointments/my-config", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "test-shop"
    assert data["working_hours_start"] == "08:00"
    assert data["working_hours_end"] == "17:00"
    assert data["slot_duration_minutes"] == "60"


def test_get_my_booking_config_not_found(client, auth_headers, mock_db):
    mock_db.execute.return_value.scalar_one_or_none.return_value = None
    resp = client.get("/appointments/my-config", headers=auth_headers)
    assert resp.status_code == 404


def test_patch_my_booking_config(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    cfg = MagicMock()
    cfg.slug = "test-shop"
    cfg.working_hours_start = "09:00"
    cfg.working_hours_end = "18:00"
    cfg.slot_duration_minutes = "30"
    mock_db.execute.return_value.scalar_one_or_none.return_value = cfg
    resp = client.patch(
        "/appointments/my-config",
        json={"working_hours_start": "09:00", "slot_duration_minutes": "30"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "test-shop"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/test_appointments.py::test_get_my_booking_config -v 2>&1 | tail -10
```

Expected: FAIL with 404 or 405 (route not found).

- [ ] **Step 3: Add routes to appointments.py**

Find the line in `backend/src/api/appointments.py` that contains `@router.get("", response_model=list[AppointmentResponse])` (the list-all-appointments route). Insert the following block **immediately before** that line:

```python
class BookingConfigUpdate(BaseModel):
    working_hours_start: Optional[str] = None
    working_hours_end: Optional[str] = None
    slot_duration_minutes: Optional[str] = None


@router.get("/my-config", response_model=BookingConfigResponse)
async def get_my_booking_config(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    result = await db.execute(
        select(BookingConfig).where(BookingConfig.shop_id == _uuid.UUID(shop_id))
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking config not found")
    return _cfg_to_response(cfg)


@router.patch("/my-config", response_model=BookingConfigResponse)
async def update_my_booking_config(
    body: BookingConfigUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    result = await db.execute(
        select(BookingConfig).where(BookingConfig.shop_id == _uuid.UUID(shop_id))
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking config not found")
    for field in ("working_hours_start", "working_hours_end", "slot_duration_minutes"):
        val = getattr(body, field, None)
        if val is not None:
            setattr(cfg, field, val)
    await db.commit()
    await db.refresh(cfg)
    return _cfg_to_response(cfg)
```

Also add `Optional` to the imports at the top of appointments.py if not already present:
```python
from typing import Optional
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/test_appointments.py -v 2>&1 | tail -20
```

Expected: all appointment tests pass including the 3 new ones.

- [ ] **Step 5: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add backend/src/api/appointments.py backend/tests/test_api/test_appointments.py
git commit -m "feat(appointments): add authenticated GET/PATCH /appointments/my-config"
```

---

### Task 3: /settings/profile + expand ShopSettingsResponse

**Files:**
- Modify: `backend/src/api/shop_settings.py`
- Modify: `backend/tests/test_api/test_shop_settings.py`

Context: `shop_settings.py` has `router` with prefix `/settings`. The `Shop` model is at `backend/src/models/shop.py` with columns `id` (UUID), `name` (String), `address` (String nullable), `labor_rate` (Numeric). The `ShopSettingsResponse` currently omits `carmd_api_key`, `synchrony_dealer_id`, `wisetack_merchant_id` — these need to be added so the Integrations section can show them. For secret keys (stripe, mitchell1, quickbooks), return a `has_*` boolean — never return the encrypted value.

- [ ] **Step 1: Write failing tests**

Add these tests to the END of `backend/tests/test_api/test_shop_settings.py`:

```python
def test_get_shop_profile(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    from decimal import Decimal
    shop = MagicMock()
    shop.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    shop.name = "Test Shop"
    shop.address = "123 Main St"
    shop.labor_rate = Decimal("120.00")
    mock_db.execute.return_value.scalar_one_or_none.return_value = shop
    resp = client.get("/settings/profile", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Shop"
    assert data["address"] == "123 Main St"
    assert data["labor_rate"] == "120.00"


def test_patch_shop_profile(client, auth_headers, mock_db):
    from unittest.mock import MagicMock
    import uuid
    from decimal import Decimal
    shop = MagicMock()
    shop.id = uuid.UUID("00000000-0000-0000-0000-000000000099")
    shop.name = "Updated Shop"
    shop.address = "456 Oak Ave"
    shop.labor_rate = Decimal("150.00")
    mock_db.execute.return_value.scalar_one_or_none.return_value = shop
    resp = client.patch(
        "/settings/profile",
        json={"name": "Updated Shop", "labor_rate": "150.00"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated Shop"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/test_shop_settings.py::test_get_shop_profile -v 2>&1 | tail -10
```

Expected: FAIL — route doesn't exist yet.

- [ ] **Step 3: Expand ShopSettingsResponse and add /profile routes**

Replace the top portion of `backend/src/api/shop_settings.py` (the Pydantic models and imports) with:

```python
import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_settings import ShopSettings
from src.models.shop import Shop

router = APIRouter(prefix="/settings", tags=["settings"])


class ShopSettingsResponse(BaseModel):
    id: str
    shop_id: str
    nav_pins: list[str]
    stripe_publishable_key: Optional[str] = None
    has_stripe_secret: bool = False
    mitchell1_enabled: bool
    has_mitchell1_key: bool = False
    synchrony_enabled: bool
    synchrony_dealer_id: Optional[str] = None
    wisetack_enabled: bool
    wisetack_merchant_id: Optional[str] = None
    quickbooks_enabled: bool
    has_quickbooks_token: bool = False
    carmd_api_key: Optional[str] = None
    financing_threshold: str


class ShopSettingsUpdate(BaseModel):
    nav_pins: Optional[list[str]] = None
    stripe_publishable_key: Optional[str] = None
    stripe_secret_key_encrypted: Optional[str] = None
    mitchell1_enabled: Optional[bool] = None
    mitchell1_api_key_encrypted: Optional[str] = None
    synchrony_enabled: Optional[bool] = None
    synchrony_dealer_id: Optional[str] = None
    wisetack_enabled: Optional[bool] = None
    wisetack_merchant_id: Optional[str] = None
    quickbooks_enabled: Optional[bool] = None
    quickbooks_refresh_token_encrypted: Optional[str] = None
    carmd_api_key: Optional[str] = None
    financing_threshold: Optional[str] = None


class ShopProfileResponse(BaseModel):
    id: str
    name: str
    address: Optional[str] = None
    labor_rate: str


class ShopProfileUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    labor_rate: Optional[str] = None
```

Then update the `_to_response` function:

```python
def _to_response(s: ShopSettings) -> ShopSettingsResponse:
    return ShopSettingsResponse(
        id=str(s.id),
        shop_id=str(s.shop_id),
        nav_pins=s.nav_pins or [],
        stripe_publishable_key=s.stripe_publishable_key,
        has_stripe_secret=bool(s.stripe_secret_key_encrypted),
        mitchell1_enabled=bool(s.mitchell1_enabled),
        has_mitchell1_key=bool(s.mitchell1_api_key_encrypted),
        synchrony_enabled=bool(s.synchrony_enabled),
        synchrony_dealer_id=s.synchrony_dealer_id,
        wisetack_enabled=bool(s.wisetack_enabled),
        wisetack_merchant_id=s.wisetack_merchant_id,
        quickbooks_enabled=bool(s.quickbooks_enabled),
        has_quickbooks_token=bool(s.quickbooks_refresh_token_encrypted),
        carmd_api_key=s.carmd_api_key,
        financing_threshold=s.financing_threshold or "500",
    )
```

Also update `update_shop_settings` to handle the new fields. Replace the PATCH route body:

```python
@router.patch("/shop", response_model=ShopSettingsResponse)
async def update_shop_settings(
    body: ShopSettingsUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    settings = await _get_or_create(uuid.UUID(shop_id), db)
    if body.nav_pins is not None:
        settings.nav_pins = body.nav_pins[:8]
    for field in (
        "stripe_publishable_key", "stripe_secret_key_encrypted",
        "mitchell1_enabled", "mitchell1_api_key_encrypted",
        "synchrony_enabled", "synchrony_dealer_id",
        "wisetack_enabled", "wisetack_merchant_id",
        "quickbooks_enabled", "quickbooks_refresh_token_encrypted",
        "carmd_api_key", "financing_threshold",
    ):
        val = getattr(body, field, None)
        if val is not None:
            setattr(settings, field, val)
    await db.commit()
    await db.refresh(settings)
    return _to_response(settings)
```

Then add the profile routes AFTER the existing `/shop` routes:

```python
@router.get("/profile", response_model=ShopProfileResponse)
async def get_shop_profile(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shop).where(Shop.id == uuid.UUID(shop_id)))
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    return ShopProfileResponse(
        id=str(shop.id),
        name=shop.name,
        address=shop.address,
        labor_rate=str(shop.labor_rate),
    )


@router.patch("/profile", response_model=ShopProfileResponse)
async def update_shop_profile(
    body: ShopProfileUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Shop).where(Shop.id == uuid.UUID(shop_id)))
    shop = result.scalar_one_or_none()
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shop not found")
    if body.name is not None:
        shop.name = body.name
    if body.address is not None:
        shop.address = body.address
    if body.labor_rate is not None:
        shop.labor_rate = Decimal(body.labor_rate)
    await db.commit()
    await db.refresh(shop)
    return ShopProfileResponse(
        id=str(shop.id),
        name=shop.name,
        address=shop.address,
        labor_rate=str(shop.labor_rate),
    )
```

- [ ] **Step 4: Run tests**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/test_shop_settings.py -v 2>&1 | tail -20
```

Expected: all pass including 2 new profile tests.

- [ ] **Step 5: Run full backend test suite**

```bash
cd /Users/joehe/workspace/projects/pitagents/backend
.venv/bin/pytest tests/test_api/ -v --tb=short 2>&1 | tail -30
```

Expected: all pass. If any existing test breaks due to expanded ShopSettingsResponse, fix the assertion to match the new field names.

- [ ] **Step 6: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add backend/src/api/shop_settings.py backend/tests/test_api/test_shop_settings.py
git commit -m "feat(settings): add /settings/profile; expand ShopSettingsResponse with integration fields"
```

---

### Task 4: Frontend types + API functions

**Files:**
- Modify: `web/lib/types.ts`
- Modify: `web/lib/api.ts`

Context: `api.ts` uses an axios instance `api` with a base URL and Bearer token interceptor. All API functions follow the pattern `export const funcName = (...) => api.method('/path').then(r => r.data)`. The `ShopSettings` interface already exists but needs the new fields from Task 3. `BookingConfig` already exists in types.ts.

- [ ] **Step 1: Add UserProfile and ShopProfile types to types.ts**

Find the line `export interface ShopSettings {` in `web/lib/types.ts`. Insert before it:

```typescript
// ── Auth / User ───────────────────────────────────────────────────────────

export interface UserProfile {
  id: string
  email: string
  name: string | null
  role: string
}

export interface ShopProfile {
  id: string
  name: string
  address: string | null
  labor_rate: string
}

```

- [ ] **Step 2: Expand ShopSettings type**

Replace the existing `ShopSettings` interface in `web/lib/types.ts` with:

```typescript
export interface ShopSettings {
  id: string
  shop_id: string
  nav_pins: string[]
  stripe_publishable_key: string | null
  has_stripe_secret: boolean
  mitchell1_enabled: boolean
  has_mitchell1_key: boolean
  synchrony_enabled: boolean
  synchrony_dealer_id: string | null
  wisetack_enabled: boolean
  wisetack_merchant_id: string | null
  quickbooks_enabled: boolean
  has_quickbooks_token: boolean
  carmd_api_key: string | null
  financing_threshold: string
}
```

- [ ] **Step 3: Add API functions to api.ts**

Find the `// ── Shop Settings ──` comment block in `web/lib/api.ts`. Insert the following block immediately before it:

```typescript
// ── Auth / User ───────────────────────────────────────────────────────────
export const getMe = (): Promise<UserProfile> =>
  api.get('/auth/me').then(r => r.data)

export const updateProfile = (name: string): Promise<UserProfile> =>
  api.patch('/auth/profile', { name }).then(r => r.data)

export const updatePassword = (currentPassword: string, newPassword: string): Promise<{ ok: boolean }> =>
  api.patch('/auth/password', { current_password: currentPassword, new_password: newPassword }).then(r => r.data)

// ── Shop Profile ──────────────────────────────────────────────────────────
export const getShopProfile = (): Promise<ShopProfile> =>
  api.get('/settings/profile').then(r => r.data)

export const updateShopProfile = (data: Partial<ShopProfile>): Promise<ShopProfile> =>
  api.patch('/settings/profile', data).then(r => r.data)

// ── Booking Config ────────────────────────────────────────────────────────
export const getMyBookingConfig = (): Promise<BookingConfig> =>
  api.get('/appointments/my-config').then(r => r.data)

export const updateMyBookingConfig = (data: Partial<BookingConfig>): Promise<BookingConfig> =>
  api.patch('/appointments/my-config', data).then(r => r.data)

```

Also add the new types to the import at line 1 of `api.ts`. Change the import to include `UserProfile` and `ShopProfile`:

```typescript
import type { Customer, Vehicle, ReportSummary, ReportDetail, Quote, QuoteLineItem, FinalizeQuoteResponse, JobCardColumn, JobCard, JobCardCreate, Invoice, ShopSettings, ShopProfile, UserProfile, Appointment, ServiceReminderConfig, InventoryItem, Vendor, PurchaseOrder, TimeEntry, Expense, PLSummary, PaymentsSummary, PaymentEvent, DiagnoseAnalyzeResult, DiagnosisItem, RepairPlanItem, TsbItem, RecallItem, MaintenanceItem, AudienceSegment, Campaign, CampaignTemplate, ShopAgent, ToolInfo, AgentCreate, AgentUpdate } from './types'
```

- [ ] **Step 4: Build to verify TypeScript**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: build succeeds. If TypeScript errors, fix the type signatures.

- [ ] **Step 5: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/lib/types.ts web/lib/api.ts
git commit -m "feat(web): add UserProfile, ShopProfile types and API functions"
```

---

### Task 5: SettingsPanel shell + AppShell wiring

**Files:**
- Create: `web/components/settings/SettingsPanel.tsx`
- Modify: `web/components/AppShell.tsx`

Context: `AppShell.tsx` currently has `settingsRef`, `settingsOpen` state, and a `SettingsDropdown` rendered in an absolutely-positioned div. Replace all of this with `settingsPanelOpen` state and a `SettingsPanel` rendered directly (it uses `position: fixed` so no wrapper needed). The panel renders section names as placeholder `<div>` elements — section components are wired in Tasks 6–10. The panel's overlay blocks clicks to the main content when open.

- [ ] **Step 1: Create SettingsPanel.tsx shell**

Create `web/components/settings/SettingsPanel.tsx`:

```tsx
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'

const SECTIONS = [
  { id: 'account',       label: 'Account',       emoji: '👤' },
  { id: 'shop',          label: 'Shop Profile',   emoji: '🏪' },
  { id: 'appearance',    label: 'Appearance',     emoji: '🎨' },
  { id: 'booking',       label: 'Booking',        emoji: '📅' },
  { id: 'notifications', label: 'Notifications',  emoji: '🔔' },
  { id: 'integrations',  label: 'Integrations',   emoji: '🔌' },
  { id: 'agents',        label: 'Agents & AI',    emoji: '🤖' },
] as const

type SectionId = typeof SECTIONS[number]['id']

interface Props {
  onClose: () => void
  onLogout: () => void
}

export function SettingsPanel({ onClose, onLogout }: Props) {
  const [active, setActive] = useState<SectionId>('account')

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0,
          background: 'rgba(0,0,0,0.45)',
          zIndex: 49,
        }}
      />

      {/* Panel */}
      <div
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0,
          width: 420, display: 'flex',
          background: 'rgba(10,10,14,0.98)',
          borderLeft: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '-20px 0 60px rgba(0,0,0,0.6)',
          zIndex: 50,
        }}
      >
        {/* Sidebar */}
        <div
          style={{
            width: 140, flexShrink: 0,
            borderRight: '1px solid rgba(255,255,255,0.07)',
            padding: '12px 8px',
            display: 'flex', flexDirection: 'column',
          }}
        >
          <div
            style={{
              fontSize: 9, textTransform: 'uppercase', letterSpacing: '.08em',
              color: 'rgba(255,255,255,0.25)', padding: '0 6px', marginBottom: 8,
            }}
          >
            Settings
          </div>

          {SECTIONS.map(s => (
            <button
              key={s.id}
              onClick={() => setActive(s.id)}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '6px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
                marginBottom: 2,
                background: active === s.id ? 'rgba(255,255,255,0.08)' : 'transparent',
                color: active === s.id ? 'var(--accent)' : 'rgba(255,255,255,0.45)',
                fontSize: 11, fontWeight: active === s.id ? 600 : 400,
              }}
            >
              {s.emoji} {s.label}
            </button>
          ))}

          <div style={{ marginTop: 'auto', borderTop: '1px solid rgba(255,255,255,0.07)', paddingTop: 8 }}>
            <button
              onClick={onLogout}
              style={{
                display: 'block', width: '100%', textAlign: 'left',
                padding: '6px 8px', borderRadius: 6, border: 'none', cursor: 'pointer',
                background: 'transparent',
                color: 'rgba(255,80,80,0.65)', fontSize: 11,
              }}
            >
              ↪ Sign out
            </button>
          </div>
        </div>

        {/* Content pane */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 20 }}>
          {/* Header */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div style={{ color: '#fff', fontSize: 14, fontWeight: 700 }}>
              {SECTIONS.find(s => s.id === active)?.label}
            </div>
            <button
              onClick={onClose}
              style={{
                background: 'none', border: 'none',
                color: 'rgba(255,255,255,0.3)', fontSize: 20,
                cursor: 'pointer', lineHeight: 1, padding: 0,
              }}
            >
              ×
            </button>
          </div>

          {/* Section placeholder — replaced in Tasks 6–10 */}
          <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
            {active} section coming soon
          </div>
        </div>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Wire SettingsPanel into AppShell**

In `web/components/AppShell.tsx`:

1. Remove the `settingsRef` ref and all outside-click `useEffect` for the dropdown.
2. Change `settingsOpen` state to `settingsPanelOpen`.
3. Remove the `import { SettingsDropdown }` line.
4. Add `import { SettingsPanel } from './settings/SettingsPanel'`.
5. Replace the avatar + dropdown block with:

The final right-side section of the nav should become:

```tsx
{/* Right side */}
<div className="ml-auto flex items-center gap-3">
  <VoiceControlWidget />
  <button
    onClick={() => setSettingsPanelOpen(v => !v)}
    style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'block' }}
  >
    <img
      src={pravatarUrl(email || 'default', 40)}
      alt="Settings"
      style={{
        width: 32, height: 32, borderRadius: '50%', objectFit: 'cover',
        border: '2px solid rgba(217,119,6,0.5)',
        display: 'block',
      }}
    />
  </button>
</div>
```

And just before the closing `</div>` of the root `AppShell` div (after `<main>`), add:

```tsx
{settingsPanelOpen && (
  <SettingsPanel
    onClose={() => setSettingsPanelOpen(false)}
    onLogout={handleLogout}
  />
)}
```

The `useEffect` for outside click and `settingsRef` can be deleted entirely since the panel has its own backdrop.

Also update the state declaration from `const [settingsOpen, setSettingsOpen] = useState(false)` to `const [settingsPanelOpen, setSettingsPanelOpen] = useState(false)`.

- [ ] **Step 3: Build**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: clean build, no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/components/settings/SettingsPanel.tsx web/components/AppShell.tsx
git commit -m "feat(web): add SettingsPanel shell; wire avatar click to panel"
```

---

### Task 6: AccountSection

**Files:**
- Create: `web/components/settings/sections/AccountSection.tsx`
- Modify: `web/components/settings/SettingsPanel.tsx`

Context: Uses `getMe`, `updateProfile`, `updatePassword` from `api.ts`. TanStack Query v5 pattern: `useQuery({ queryKey: ['me'], queryFn: getMe })`. Mutations use `useMutation({ mutationFn: ..., onSuccess: ..., onError: ... })`. Form state is local. `user?.name` is `string | null`.

- [ ] **Step 1: Create AccountSection.tsx**

Create `web/components/settings/sections/AccountSection.tsx`:

```tsx
'use client'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMe, updateProfile, updatePassword } from '@/lib/api'

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '8px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
  letterSpacing: '.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 10,
}

function SaveButton({ label, pending }: { label: string; pending: boolean }) {
  return (
    <button
      type="submit"
      disabled={pending}
      style={{
        background: 'var(--accent)', color: '#000', border: 'none',
        borderRadius: 6, padding: '7px 16px', fontSize: 12, fontWeight: 700,
        cursor: pending ? 'not-allowed' : 'pointer', opacity: pending ? 0.6 : 1,
      }}
    >
      {pending ? 'Saving…' : label}
    </button>
  )
}

function InlineMsg({ msg }: { msg: { type: 'ok' | 'err'; text: string } | null }) {
  if (!msg) return null
  return (
    <div style={{
      fontSize: 11, marginTop: 8,
      color: msg.type === 'ok' ? 'rgba(74,222,128,0.9)' : 'rgba(239,68,68,0.9)',
    }}>
      {msg.text}
    </div>
  )
}

export function AccountSection() {
  const qc = useQueryClient()
  const { data: user } = useQuery({ queryKey: ['me'], queryFn: getMe })

  const [name, setName] = useState('')
  const [profileMsg, setProfileMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  const [pwd, setPwd] = useState({ current: '', next: '', confirm: '' })
  const [pwdMsg, setPwdMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (user) setName(user.name ?? '')
  }, [user])

  const saveProfile = useMutation({
    mutationFn: () => updateProfile(name),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['me'] })
      setProfileMsg({ type: 'ok', text: 'Saved' })
      setTimeout(() => setProfileMsg(null), 2500)
    },
    onError: (e: Error) => setProfileMsg({ type: 'err', text: e.message }),
  })

  const changePwd = useMutation({
    mutationFn: () => {
      if (pwd.next !== pwd.confirm) throw new Error("Passwords don't match")
      if (pwd.next.length < 8) throw new Error('New password must be at least 8 characters')
      return updatePassword(pwd.current, pwd.next)
    },
    onSuccess: () => {
      setPwd({ current: '', next: '', confirm: '' })
      setPwdMsg({ type: 'ok', text: 'Password changed' })
      setTimeout(() => setPwdMsg(null), 2500)
    },
    onError: (e: Error) => setPwdMsg({ type: 'err', text: e.message }),
  })

  return (
    <div>
      {/* Profile */}
      <div style={sectionHeadingStyle}>Profile</div>
      <form
        onSubmit={e => { e.preventDefault(); saveProfile.mutate() }}
        style={{ marginBottom: 24 }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%', flexShrink: 0,
            background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <span style={{ color: '#000', fontSize: 12, fontWeight: 700 }}>
              {(user?.name || user?.email || '?')[0].toUpperCase()}
            </span>
          </div>
          <div style={{ flex: 1 }}>
            <label style={labelStyle}>Display name</label>
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              style={fieldStyle}
              placeholder="Your name"
            />
          </div>
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>Email</label>
          <input
            value={user?.email ?? ''}
            readOnly
            style={{ ...fieldStyle, color: 'rgba(255,255,255,0.35)', cursor: 'default' }}
          />
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <SaveButton label="Save Profile" pending={saveProfile.isPending} />
        </div>
        <InlineMsg msg={profileMsg} />
      </form>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', marginBottom: 20 }} />

      {/* Security */}
      <div style={sectionHeadingStyle}>Security</div>
      <form onSubmit={e => { e.preventDefault(); changePwd.mutate() }}>
        <div style={{ marginBottom: 8 }}>
          <label style={labelStyle}>Current password</label>
          <input
            type="password"
            value={pwd.current}
            onChange={e => setPwd(p => ({ ...p, current: e.target.value }))}
            style={fieldStyle}
            autoComplete="current-password"
          />
        </div>
        <div style={{ marginBottom: 8 }}>
          <label style={labelStyle}>New password</label>
          <input
            type="password"
            value={pwd.next}
            onChange={e => setPwd(p => ({ ...p, next: e.target.value }))}
            style={fieldStyle}
            autoComplete="new-password"
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={labelStyle}>Confirm new password</label>
          <input
            type="password"
            value={pwd.confirm}
            onChange={e => setPwd(p => ({ ...p, confirm: e.target.value }))}
            style={fieldStyle}
            autoComplete="new-password"
          />
        </div>
        <SaveButton label="Change Password" pending={changePwd.isPending} />
        <InlineMsg msg={pwdMsg} />
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Wire AccountSection into SettingsPanel**

In `web/components/settings/SettingsPanel.tsx`:

1. Add import at top: `import { AccountSection } from './sections/AccountSection'`
2. Replace the `{/* Section placeholder */}` div with:

```tsx
{active === 'account' && <AccountSection />}
{active !== 'account' && (
  <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
    {active} section coming soon
  </div>
)}
```

- [ ] **Step 3: Build**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: clean build.

- [ ] **Step 4: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/components/settings/sections/AccountSection.tsx web/components/settings/SettingsPanel.tsx
git commit -m "feat(web): add AccountSection (profile + password change)"
```

---

### Task 7: ShopProfileSection + AppearanceSection

**Files:**
- Create: `web/components/settings/sections/ShopProfileSection.tsx`
- Create: `web/components/settings/sections/AppearanceSection.tsx`
- Modify: `web/components/settings/SettingsPanel.tsx`

Context: `ShopProfile` uses `getShopProfile` / `updateShopProfile`. `AppearanceSection` migrates the accent color picker from `web/app/settings/page.tsx` (`AppearanceTab` component) and the background theme switcher from `SettingsDropdown`. Uses `useAccent` from `ThemeProvider` and `useTheme` from `hooks/useTheme`.

- [ ] **Step 1: Create ShopProfileSection.tsx**

Create `web/components/settings/sections/ShopProfileSection.tsx`:

```tsx
'use client'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getShopProfile, updateShopProfile } from '@/lib/api'

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '8px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

export function ShopProfileSection() {
  const qc = useQueryClient()
  const { data: shop } = useQuery({ queryKey: ['shop-profile'], queryFn: getShopProfile })

  const [form, setForm] = useState({ name: '', address: '', labor_rate: '' })
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (shop) {
      setForm({
        name: shop.name,
        address: shop.address ?? '',
        labor_rate: shop.labor_rate,
      })
    }
  }, [shop])

  const save = useMutation({
    mutationFn: () => updateShopProfile({
      name: form.name,
      address: form.address || undefined,
      labor_rate: form.labor_rate,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shop-profile'] })
      setMsg({ type: 'ok', text: 'Saved' })
      setTimeout(() => setMsg(null), 2500)
    },
    onError: (e: Error) => setMsg({ type: 'err', text: e.message }),
  })

  function field(key: keyof typeof form, label: string, placeholder?: string) {
    return (
      <div style={{ marginBottom: 12 }}>
        <label style={labelStyle}>{label}</label>
        <input
          value={form[key]}
          onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
          style={fieldStyle}
          placeholder={placeholder}
        />
      </div>
    )
  }

  return (
    <form onSubmit={e => { e.preventDefault(); save.mutate() }}>
      {field('name', 'Shop name', 'AutoShop')}
      {field('address', 'Address', '123 Main St')}
      {field('labor_rate', 'Labor rate ($/hr)', '120.00')}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <button
          type="submit"
          disabled={save.isPending}
          style={{
            background: 'var(--accent)', color: '#000', border: 'none',
            borderRadius: 6, padding: '7px 16px', fontSize: 12, fontWeight: 700,
            cursor: save.isPending ? 'not-allowed' : 'pointer', opacity: save.isPending ? 0.6 : 1,
          }}
        >
          {save.isPending ? 'Saving…' : 'Save'}
        </button>
      </div>
      {msg && (
        <div style={{ fontSize: 11, marginTop: 8, color: msg.type === 'ok' ? 'rgba(74,222,128,0.9)' : 'rgba(239,68,68,0.9)' }}>
          {msg.text}
        </div>
      )}
    </form>
  )
}
```

- [ ] **Step 2: Create AppearanceSection.tsx**

Create `web/components/settings/sections/AppearanceSection.tsx`:

```tsx
'use client'
import { useState } from 'react'
import { useAccent } from '@/components/ThemeProvider'
import { useTheme, BgTheme } from '@/hooks/useTheme'

const ACCENT_PRESETS = [
  { label: 'Amber',   value: '#d97706' },
  { label: 'Indigo',  value: '#4f46e5' },
  { label: 'Emerald', value: '#059669' },
  { label: 'Sky',     value: '#0284c7' },
  { label: 'Rose',    value: '#e11d48' },
  { label: 'Violet',  value: '#7c3aed' },
]

const BG_THEMES: { id: BgTheme; label: string; swatch: string }[] = [
  { id: 'dark',  label: 'Dark',  swatch: 'linear-gradient(135deg,#080808,#1c1c1c)' },
  { id: 'moody', label: 'Moody', swatch: 'linear-gradient(135deg,rgba(10,8,5,0.9),rgba(30,20,10,0.7))' },
  { id: 'vivid', label: 'Vivid', swatch: 'linear-gradient(135deg,rgba(220,210,190,0.6),rgba(180,170,150,0.4))' },
]

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
  letterSpacing: '.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 10,
}

export function AppearanceSection() {
  const { accent, setAccent } = useAccent()
  const { theme, setTheme } = useTheme()
  const [custom, setCustom] = useState(accent)

  function applyCustom() {
    if (/^#[0-9a-fA-F]{6}$/.test(custom)) setAccent(custom)
  }

  return (
    <div>
      <div style={sectionHeadingStyle}>Accent Color</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        {ACCENT_PRESETS.map(p => (
          <button
            key={p.value}
            onClick={() => { setAccent(p.value); setCustom(p.value) }}
            title={p.label}
            style={{
              width: 30, height: 30, borderRadius: 8, border: 'none', cursor: 'pointer',
              background: p.value,
              outline: accent === p.value ? `2px solid ${p.value}` : '2px solid transparent',
              outlineOffset: 2,
              boxShadow: accent === p.value ? '0 0 0 1px rgba(255,255,255,0.2)' : 'none',
            }}
          />
        ))}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 24 }}>
        <input
          type="color"
          value={custom}
          onChange={e => { setCustom(e.target.value); setAccent(e.target.value) }}
          style={{ width: 30, height: 30, borderRadius: 6, border: 'none', cursor: 'pointer', padding: 0, background: 'transparent' }}
        />
        <input
          type="text"
          value={custom}
          onChange={e => setCustom(e.target.value)}
          onBlur={applyCustom}
          onKeyDown={e => e.key === 'Enter' && applyCustom()}
          placeholder="#d97706"
          style={{
            flex: 1, background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
            padding: '6px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)', outline: 'none',
          }}
        />
        <button
          onClick={applyCustom}
          style={{
            background: 'var(--accent)', color: '#000', border: 'none',
            borderRadius: 6, padding: '6px 12px', fontSize: 12, fontWeight: 700, cursor: 'pointer',
          }}
        >
          Apply
        </button>
      </div>

      <div style={{ height: 1, background: 'rgba(255,255,255,0.07)', marginBottom: 20 }} />

      <div style={sectionHeadingStyle}>Background Theme</div>
      <div style={{ display: 'flex', gap: 8 }}>
        {BG_THEMES.map(t => (
          <button
            key={t.id}
            onClick={() => setTheme(t.id)}
            style={{
              flex: 1, padding: '8px 4px', borderRadius: 8, cursor: 'pointer',
              textAlign: 'center', fontSize: 11, fontWeight: 500,
              color: theme === t.id ? 'var(--accent)' : 'rgba(255,255,255,0.55)',
              border: theme === t.id ? '1px solid var(--accent)' : '1px solid rgba(255,255,255,0.09)',
              background: theme === t.id ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.03)',
            }}
          >
            <div style={{ width: '100%', height: 22, borderRadius: 4, marginBottom: 4, background: t.swatch }} />
            {t.label}
          </button>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Wire both sections into SettingsPanel**

In `web/components/settings/SettingsPanel.tsx`, add imports:

```tsx
import { ShopProfileSection } from './sections/ShopProfileSection'
import { AppearanceSection } from './sections/AppearanceSection'
```

Replace the placeholder block with:

```tsx
{active === 'account' && <AccountSection />}
{active === 'shop' && <ShopProfileSection />}
{active === 'appearance' && <AppearanceSection />}
{!['account', 'shop', 'appearance'].includes(active) && (
  <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
    {active} section coming soon
  </div>
)}
```

- [ ] **Step 4: Build**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: clean build.

- [ ] **Step 5: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/components/settings/sections/ShopProfileSection.tsx web/components/settings/sections/AppearanceSection.tsx web/components/settings/SettingsPanel.tsx
git commit -m "feat(web): add ShopProfileSection and AppearanceSection"
```

---

### Task 8: BookingSection + NotificationsSection

**Files:**
- Create: `web/components/settings/sections/BookingSection.tsx`
- Create: `web/components/settings/sections/NotificationsSection.tsx`
- Modify: `web/components/settings/SettingsPanel.tsx`

Context: `BookingSection` uses `getMyBookingConfig` / `updateMyBookingConfig` from api.ts. `NotificationsSection` uses existing `fetchReminderConfigs` / `updateReminderConfig` from api.ts. `ServiceReminderConfig` type already exists in types.ts. If the booking config returns 404 (no config row), show a "Not configured" message.

- [ ] **Step 1: Create BookingSection.tsx**

Create `web/components/settings/sections/BookingSection.tsx`:

```tsx
'use client'
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getMyBookingConfig, updateMyBookingConfig } from '@/lib/api'

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '8px 10px', fontSize: 12, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box',
}

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

export function BookingSection() {
  const qc = useQueryClient()
  const { data: cfg, isError } = useQuery({
    queryKey: ['my-booking-config'],
    queryFn: getMyBookingConfig,
    retry: false,
  })

  const [form, setForm] = useState({
    working_hours_start: '08:00',
    working_hours_end: '17:00',
    slot_duration_minutes: '60',
  })
  const [msg, setMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null)

  useEffect(() => {
    if (cfg) {
      setForm({
        working_hours_start: cfg.working_hours_start,
        working_hours_end: cfg.working_hours_end,
        slot_duration_minutes: cfg.slot_duration_minutes,
      })
    }
  }, [cfg])

  const save = useMutation({
    mutationFn: () => updateMyBookingConfig(form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-booking-config'] })
      setMsg({ type: 'ok', text: 'Saved' })
      setTimeout(() => setMsg(null), 2500)
    },
    onError: (e: Error) => setMsg({ type: 'err', text: e.message }),
  })

  if (isError) {
    return (
      <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 12 }}>
        No booking config found. Run the demo seed or contact support.
      </div>
    )
  }

  return (
    <div>
      {cfg?.slug && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ ...labelStyle }}>Booking link</div>
          <div style={{
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 6, padding: '8px 10px', fontSize: 11,
            color: 'rgba(255,255,255,0.45)', fontFamily: 'monospace',
          }}>
            /book/{cfg.slug}
          </div>
        </div>
      )}

      <form onSubmit={e => { e.preventDefault(); save.mutate() }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
          <div>
            <label style={labelStyle}>Open time</label>
            <input
              type="time"
              value={form.working_hours_start}
              onChange={e => setForm(f => ({ ...f, working_hours_start: e.target.value }))}
              style={fieldStyle}
            />
          </div>
          <div>
            <label style={labelStyle}>Close time</label>
            <input
              type="time"
              value={form.working_hours_end}
              onChange={e => setForm(f => ({ ...f, working_hours_end: e.target.value }))}
              style={fieldStyle}
            />
          </div>
        </div>
        <div style={{ marginBottom: 16 }}>
          <label style={labelStyle}>Slot duration (minutes)</label>
          <select
            value={form.slot_duration_minutes}
            onChange={e => setForm(f => ({ ...f, slot_duration_minutes: e.target.value }))}
            style={{ ...fieldStyle, cursor: 'pointer' }}
          >
            {['15', '30', '45', '60', '90', '120'].map(v => (
              <option key={v} value={v}>{v} min</option>
            ))}
          </select>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button
            type="submit"
            disabled={save.isPending}
            style={{
              background: 'var(--accent)', color: '#000', border: 'none',
              borderRadius: 6, padding: '7px 16px', fontSize: 12, fontWeight: 700,
              cursor: save.isPending ? 'not-allowed' : 'pointer', opacity: save.isPending ? 0.6 : 1,
            }}
          >
            {save.isPending ? 'Saving…' : 'Save'}
          </button>
        </div>
        {msg && (
          <div style={{ fontSize: 11, marginTop: 8, color: msg.type === 'ok' ? 'rgba(74,222,128,0.9)' : 'rgba(239,68,68,0.9)' }}>
            {msg.text}
          </div>
        )}
      </form>
    </div>
  )
}
```

- [ ] **Step 2: Create NotificationsSection.tsx**

Create `web/components/settings/sections/NotificationsSection.tsx`:

```tsx
'use client'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchReminderConfigs, updateReminderConfig } from '@/lib/api'
import type { ServiceReminderConfig } from '@/lib/types'
import { useState } from 'react'

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

const sectionHeadingStyle: React.CSSProperties = {
  fontSize: 10, fontWeight: 600, textTransform: 'uppercase',
  letterSpacing: '.07em', color: 'rgba(255,255,255,0.3)', marginBottom: 10,
}

function ReminderRow({ cfg }: { cfg: ServiceReminderConfig }) {
  const qc = useQueryClient()
  const [windowStart, setWindowStart] = useState(String(cfg.window_start_months))
  const [windowEnd, setWindowEnd] = useState(String(cfg.window_end_months))
  const [smsEnabled, setSmsEnabled] = useState(cfg.sms_enabled)
  const [emailEnabled, setEmailEnabled] = useState(cfg.email_enabled)
  const [msg, setMsg] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: () => updateReminderConfig(cfg.id, {
      window_start_months: Number(windowStart),
      window_end_months: Number(windowEnd),
      sms_enabled: smsEnabled,
      email_enabled: emailEnabled,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reminder-configs'] })
      setMsg('Saved')
      setTimeout(() => setMsg(null), 2000)
    },
  })

  const inputStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
    borderRadius: 5, padding: '5px 8px', fontSize: 11, color: 'rgba(255,255,255,0.8)',
    outline: 'none', width: 48,
  }

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
      borderRadius: 8, padding: '12px 14px', marginBottom: 8,
    }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: '#fff', marginBottom: 8, textTransform: 'capitalize' }}>
        {cfg.service_type.replace(/_/g, ' ')}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>Remind</span>
        <input value={windowStart} onChange={e => setWindowStart(e.target.value)} style={inputStyle} type="number" min="1" />
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>–</span>
        <input value={windowEnd} onChange={e => setWindowEnd(e.target.value)} style={inputStyle} type="number" min="1" />
        <span style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)' }}>months out</span>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'rgba(255,255,255,0.5)', cursor: 'pointer', marginLeft: 4 }}>
          <input type="checkbox" checked={smsEnabled} onChange={e => setSmsEnabled(e.target.checked)} />
          SMS
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11, color: 'rgba(255,255,255,0.5)', cursor: 'pointer' }}>
          <input type="checkbox" checked={emailEnabled} onChange={e => setEmailEnabled(e.target.checked)} />
          Email
        </label>
        <button
          onClick={() => save.mutate()}
          disabled={save.isPending}
          style={{
            marginLeft: 'auto', background: 'var(--accent)', color: '#000', border: 'none',
            borderRadius: 5, padding: '4px 10px', fontSize: 11, fontWeight: 700, cursor: 'pointer',
            opacity: save.isPending ? 0.6 : 1,
          }}
        >
          {save.isPending ? '…' : msg ?? 'Save'}
        </button>
      </div>
    </div>
  )
}

export function NotificationsSection() {
  const { data: configs = [], isLoading } = useQuery({
    queryKey: ['reminder-configs'],
    queryFn: fetchReminderConfigs,
  })

  if (isLoading) {
    return <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>Loading…</div>
  }

  return (
    <div>
      <div style={sectionHeadingStyle}>Service Reminder Windows</div>
      <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.35)', marginBottom: 14 }}>
        Configure when automatic reminders are sent to customers before their next service is due.
      </div>
      {configs.length === 0 && (
        <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
          No reminder configs found. Add them from the Reminders page.
        </div>
      )}
      {configs.map(cfg => <ReminderRow key={cfg.id} cfg={cfg} />)}
    </div>
  )
}
```

- [ ] **Step 3: Wire both into SettingsPanel**

In `web/components/settings/SettingsPanel.tsx`, add imports:

```tsx
import { BookingSection } from './sections/BookingSection'
import { NotificationsSection } from './sections/NotificationsSection'
```

Update the section rendering block:

```tsx
{active === 'account' && <AccountSection />}
{active === 'shop' && <ShopProfileSection />}
{active === 'appearance' && <AppearanceSection />}
{active === 'booking' && <BookingSection />}
{active === 'notifications' && <NotificationsSection />}
{!['account', 'shop', 'appearance', 'booking', 'notifications'].includes(active) && (
  <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>
    {active} section coming soon
  </div>
)}
```

- [ ] **Step 4: Build**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: clean build.

- [ ] **Step 5: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/components/settings/sections/BookingSection.tsx web/components/settings/sections/NotificationsSection.tsx web/components/settings/SettingsPanel.tsx
git commit -m "feat(web): add BookingSection and NotificationsSection"
```

---

### Task 9: IntegrationsSection

**Files:**
- Create: `web/components/settings/sections/IntegrationsSection.tsx`
- Modify: `web/components/settings/SettingsPanel.tsx`

Context: Uses `getShopSettings` / `updateShopSettings` from api.ts. Shows each integration as a card with a "Connected" / "Not connected" status badge. Secret keys are write-only — show a `has_*` boolean from the API to display status. When saving a key, clear the input after success.

- [ ] **Step 1: Create IntegrationsSection.tsx**

Create `web/components/settings/sections/IntegrationsSection.tsx`:

```tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getShopSettings, updateShopSettings } from '@/lib/api'

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 10, fontWeight: 600,
  textTransform: 'uppercase', letterSpacing: '.06em',
  color: 'rgba(255,255,255,0.3)', marginBottom: 5,
}

const fieldStyle: React.CSSProperties = {
  width: '100%', background: 'rgba(255,255,255,0.05)',
  border: '1px solid rgba(255,255,255,0.09)', borderRadius: 6,
  padding: '7px 10px', fontSize: 11, color: 'rgba(255,255,255,0.85)',
  outline: 'none', boxSizing: 'border-box', fontFamily: 'monospace',
}

function StatusBadge({ connected }: { connected: boolean }) {
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, padding: '2px 7px', borderRadius: 4,
      background: connected ? 'rgba(74,222,128,0.12)' : 'rgba(255,255,255,0.06)',
      color: connected ? 'rgba(74,222,128,0.9)' : 'rgba(255,255,255,0.35)',
      border: connected ? '1px solid rgba(74,222,128,0.25)' : '1px solid rgba(255,255,255,0.08)',
    }}>
      {connected ? 'Connected' : 'Not connected'}
    </span>
  )
}

function IntegrationCard({
  title, connected, children,
}: { title: string; connected: boolean; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
      borderRadius: 8, marginBottom: 8, overflow: 'hidden',
    }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          width: '100%', padding: '12px 14px', background: 'none', border: 'none', cursor: 'pointer',
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 600, color: '#fff' }}>{title}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <StatusBadge connected={connected} />
          <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
        </div>
      </button>
      {open && (
        <div style={{ padding: '0 14px 14px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

export function IntegrationsSection() {
  const qc = useQueryClient()
  const { data: settings } = useQuery({ queryKey: ['shop-settings'], queryFn: getShopSettings })

  const [stripe, setStripe] = useState({ pub: '', secret: '' })
  const [carmd, setCarmd] = useState('')
  const [mitchell, setMitchell] = useState(false)
  const [qb, setQb] = useState(false)
  const [synchrony, setSynchrony] = useState({ enabled: false, dealer_id: '' })
  const [wisetack, setWisetack] = useState({ enabled: false, merchant_id: '' })
  const [msg, setMsg] = useState<string | null>(null)

  const save = useMutation({
    mutationFn: (data: Parameters<typeof updateShopSettings>[0]) => updateShopSettings(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shop-settings'] })
      setMsg('Saved')
      setTimeout(() => setMsg(null), 2500)
    },
  })

  if (!settings) {
    return <div style={{ color: 'rgba(255,255,255,0.3)', fontSize: 12 }}>Loading…</div>
  }

  return (
    <div>
      <IntegrationCard title="Stripe" connected={settings.has_stripe_secret}>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Publishable key</label>
          <input
            value={stripe.pub || settings.stripe_publishable_key || ''}
            onChange={e => setStripe(s => ({ ...s, pub: e.target.value }))}
            style={fieldStyle}
            placeholder="pk_live_..."
          />
        </div>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Secret key {settings.has_stripe_secret && '(already set)'}</label>
          <input
            type="password"
            value={stripe.secret}
            onChange={e => setStripe(s => ({ ...s, secret: e.target.value }))}
            style={fieldStyle}
            placeholder={settings.has_stripe_secret ? '••••••••' : 'sk_live_...'}
          />
        </div>
        <button
          onClick={() => save.mutate({
            stripe_publishable_key: stripe.pub || undefined,
            stripe_secret_key_encrypted: stripe.secret || undefined,
          })}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="CarMD Diagnostics" connected={!!settings.carmd_api_key}>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>API key</label>
          <input
            value={carmd || settings.carmd_api_key || ''}
            onChange={e => setCarmd(e.target.value)}
            style={fieldStyle}
            placeholder="carmd-api-key"
          />
        </div>
        <button
          onClick={() => save.mutate({ carmd_api_key: carmd || undefined })}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="Mitchell1" connected={settings.mitchell1_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={mitchell || settings.mitchell1_enabled}
            onChange={e => setMitchell(e.target.checked)}
          />
          Enable Mitchell1 integration
        </label>
        <button
          onClick={() => save.mutate({ mitchell1_enabled: mitchell })}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="QuickBooks" connected={settings.quickbooks_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={qb || settings.quickbooks_enabled}
            onChange={e => setQb(e.target.checked)}
          />
          Enable QuickBooks sync
        </label>
        <button
          onClick={() => save.mutate({ quickbooks_enabled: qb })}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="Synchrony Financing" connected={settings.synchrony_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={synchrony.enabled || settings.synchrony_enabled}
            onChange={e => setSynchrony(s => ({ ...s, enabled: e.target.checked }))}
          />
          Enable Synchrony
        </label>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Dealer ID</label>
          <input
            value={synchrony.dealer_id || settings.synchrony_dealer_id || ''}
            onChange={e => setSynchrony(s => ({ ...s, dealer_id: e.target.value }))}
            style={fieldStyle}
            placeholder="dealer-id"
          />
        </div>
        <button
          onClick={() => save.mutate({ synchrony_enabled: synchrony.enabled, synchrony_dealer_id: synchrony.dealer_id || undefined })}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
        >
          Save
        </button>
      </IntegrationCard>

      <IntegrationCard title="Wisetack Financing" connected={settings.wisetack_enabled}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12, color: 'rgba(255,255,255,0.7)', marginBottom: 8 }}>
          <input
            type="checkbox"
            checked={wisetack.enabled || settings.wisetack_enabled}
            onChange={e => setWisetack(s => ({ ...s, enabled: e.target.checked }))}
          />
          Enable Wisetack
        </label>
        <div style={{ marginBottom: 10 }}>
          <label style={labelStyle}>Merchant ID</label>
          <input
            value={wisetack.merchant_id || settings.wisetack_merchant_id || ''}
            onChange={e => setWisetack(s => ({ ...s, merchant_id: e.target.value }))}
            style={fieldStyle}
            placeholder="merchant-id"
          />
        </div>
        <button
          onClick={() => save.mutate({ wisetack_enabled: wisetack.enabled, wisetack_merchant_id: wisetack.merchant_id || undefined })}
          style={{ background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6, padding: '6px 14px', fontSize: 11, fontWeight: 700, cursor: 'pointer' }}
        >
          Save
        </button>
      </IntegrationCard>

      {msg && (
        <div style={{ fontSize: 11, marginTop: 8, color: 'rgba(74,222,128,0.9)' }}>{msg}</div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Wire into SettingsPanel**

In `web/components/settings/SettingsPanel.tsx`, add:

```tsx
import { IntegrationsSection } from './sections/IntegrationsSection'
```

Update the rendering block to add:

```tsx
{active === 'integrations' && <IntegrationsSection />}
```

Remove `'integrations'` from the "coming soon" exclusion list.

- [ ] **Step 3: Build**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: clean build.

- [ ] **Step 4: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/components/settings/sections/IntegrationsSection.tsx web/components/settings/SettingsPanel.tsx
git commit -m "feat(web): add IntegrationsSection"
```

---

### Task 10: AgentsSection + cleanup

**Files:**
- Create: `web/components/settings/sections/AgentsSection.tsx`
- Modify: `web/components/settings/SettingsPanel.tsx`
- Delete: `web/components/SettingsDropdown.tsx`
- Replace: `web/app/settings/page.tsx`

Context: `AgentsSection` is a direct migration of `AgentsTab` and `AgentForm` from `web/app/settings/page.tsx`. Copy the full component logic — it already works, just needs to live in the panel. After migration, `web/app/settings/page.tsx` becomes a simple redirect.

- [ ] **Step 1: Create AgentsSection.tsx**

Create `web/components/settings/sections/AgentsSection.tsx` by copying the `AgentsTab` and `AgentForm` components from `web/app/settings/page.tsx`. The file should be:

```tsx
'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAgents, fetchToolRegistry, createAgent, updateAgent, deleteAgent } from '@/lib/api'
import type { ShopAgent, ToolInfo, AgentCreate } from '@/lib/types'

export function AgentsSection() {
  const qc = useQueryClient()
  const { data: agents = [] } = useQuery({ queryKey: ['agents'], queryFn: fetchAgents })
  const { data: tools = [] } = useQuery({ queryKey: ['tool-registry'], queryFn: fetchToolRegistry })
  const [editing, setEditing] = useState<ShopAgent | null>(null)
  const [creating, setCreating] = useState(false)

  const del = useMutation({
    mutationFn: deleteAgent,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['agents'] }),
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#f9fafb' }}>Agents</span>
        <button
          onClick={() => { setCreating(true); setEditing(null) }}
          style={{
            background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6,
            padding: '6px 12px', cursor: 'pointer', fontSize: 12, fontWeight: 600,
          }}
        >
          + New Agent
        </button>
      </div>

      {agents.map(agent => (
        <div key={agent.id} style={{
          background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
          borderLeft: `3px solid ${agent.accent_color}`,
          borderRadius: 8, padding: '10px 14px', marginBottom: 8,
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ color: '#f9fafb', fontWeight: 600, fontSize: 13 }}>{agent.name}</div>
            <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: 11, marginTop: 2 }}>{agent.role_tagline}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => { setEditing(agent); setCreating(false) }}
              style={{
                background: 'rgba(255,255,255,0.07)', border: '1px solid rgba(255,255,255,0.1)',
                color: 'rgba(255,255,255,0.75)', borderRadius: 5, padding: '5px 10px',
                cursor: 'pointer', fontSize: 11,
              }}
            >
              Edit
            </button>
            <button
              onClick={() => del.mutate(agent.id)}
              style={{
                background: 'none', border: '1px solid rgba(255,255,255,0.08)',
                color: 'rgba(255,255,255,0.4)', borderRadius: 5, padding: '5px 10px',
                cursor: 'pointer', fontSize: 11,
              }}
            >
              Delete
            </button>
          </div>
        </div>
      ))}

      {(creating || editing) && (
        <AgentForm
          agent={editing}
          tools={tools}
          onClose={() => { setCreating(false); setEditing(null) }}
          onSaved={() => { qc.invalidateQueries({ queryKey: ['agents'] }); setCreating(false); setEditing(null) }}
        />
      )}
    </div>
  )
}

function AgentForm({
  agent, tools, onClose, onSaved,
}: {
  agent: ShopAgent | null
  tools: ToolInfo[]
  onClose: () => void
  onSaved: () => void
}) {
  const isNew = !agent
  const [name, setName] = useState(agent?.name ?? '')
  const [tagline, setTagline] = useState(agent?.role_tagline ?? '')
  const [color, setColor] = useState(agent?.accent_color ?? '#d97706')
  const [initials, setInitials] = useState(agent?.initials ?? '')
  const [prompt, setPrompt] = useState(agent?.system_prompt ?? '')
  const [selectedTools, setSelectedTools] = useState<string[]>(agent?.tools ?? [])
  const [showPrompt, setShowPrompt] = useState(false)

  const save = useMutation({
    mutationFn: () => {
      const payload: AgentCreate = { name, role_tagline: tagline, accent_color: color, initials, system_prompt: prompt, tools: selectedTools }
      return isNew ? createAgent(payload) : updateAgent(agent!.id, payload)
    },
    onSuccess: onSaved,
  })

  const inputStyle: React.CSSProperties = {
    background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.09)',
    color: '#fff', borderRadius: 6, padding: '7px 10px', fontSize: 12,
    width: '100%', outline: 'none', boxSizing: 'border-box',
  }
  const labelStyle: React.CSSProperties = {
    color: 'rgba(255,255,255,0.3)', fontSize: 10, fontWeight: 600,
    textTransform: 'uppercase', letterSpacing: '.05em', display: 'block', marginBottom: 4,
  }
  const toggleTool = (id: string) =>
    setSelectedTools(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id])

  return (
    <div style={{
      background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 10, padding: 16, marginTop: 12,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#f9fafb' }}>
          {isNew ? 'New Agent' : `Edit: ${agent!.name}`}
        </span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.4)', cursor: 'pointer', fontSize: 18 }}>×</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 10 }}>
        <div><label style={labelStyle}>Name</label><input value={name} onChange={e => setName(e.target.value)} style={inputStyle} placeholder="Service Advisor" /></div>
        <div><label style={labelStyle}>Initials</label><input value={initials} onChange={e => setInitials(e.target.value.toUpperCase().slice(0, 3))} style={inputStyle} placeholder="SA" maxLength={3} /></div>
      </div>

      <div style={{ marginBottom: 10 }}>
        <label style={labelStyle}>Role Tagline</label>
        <input value={tagline} onChange={e => setTagline(e.target.value)} style={inputStyle} placeholder="Front desk · Customer intake" />
      </div>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Accent Color</label>
        <div style={{ display: 'flex', gap: 6 }}>
          {['#d97706', '#3b82f6', '#06b6d4', '#22c55e', '#a855f7', '#ef4444'].map(c => (
            <button key={c} onClick={() => setColor(c)} style={{ width: 22, height: 22, borderRadius: '50%', background: c, border: 'none', cursor: 'pointer', outline: color === c ? `2px solid ${c}` : 'none', outlineOffset: 2 }} />
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 14 }}>
        <label style={labelStyle}>Tools</label>
        {tools.map(t => (
          <label key={t.id} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer', marginBottom: 6 }}>
            <input type="checkbox" checked={selectedTools.includes(t.id)} onChange={() => toggleTool(t.id)} style={{ marginTop: 2 }} />
            <div>
              <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)', fontWeight: 500 }}>{t.label}</div>
              <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)' }}>{t.description}</div>
            </div>
          </label>
        ))}
      </div>

      <div style={{ marginBottom: 14 }}>
        <button onClick={() => setShowPrompt(v => !v)} style={{ background: 'none', border: 'none', color: 'rgba(255,255,255,0.5)', cursor: 'pointer', fontSize: 11, padding: 0, textDecoration: 'underline' }}>
          {showPrompt ? 'Hide' : 'Edit'} system prompt
        </button>
        {showPrompt && (
          <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={5}
            style={{ ...inputStyle, marginTop: 6, resize: 'vertical', fontFamily: 'monospace', fontSize: 11 }} />
        )}
      </div>

      <button
        onClick={() => save.mutate()}
        disabled={save.isPending || !name || !initials}
        style={{
          background: 'var(--accent)', color: '#000', border: 'none', borderRadius: 6,
          padding: '8px 18px', cursor: 'pointer', fontWeight: 700, fontSize: 12,
          opacity: (save.isPending || !name || !initials) ? 0.5 : 1,
        }}
      >
        {save.isPending ? 'Saving…' : isNew ? 'Create Agent' : 'Save Changes'}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Wire AgentsSection into SettingsPanel and complete the section router**

In `web/components/settings/SettingsPanel.tsx`, add:

```tsx
import { AgentsSection } from './sections/AgentsSection'
```

Replace the full section rendering block with the final version:

```tsx
{active === 'account' && <AccountSection />}
{active === 'shop' && <ShopProfileSection />}
{active === 'appearance' && <AppearanceSection />}
{active === 'booking' && <BookingSection />}
{active === 'notifications' && <NotificationsSection />}
{active === 'integrations' && <IntegrationsSection />}
{active === 'agents' && <AgentsSection />}
```

- [ ] **Step 3: Delete SettingsDropdown.tsx**

```bash
rm /Users/joehe/workspace/projects/pitagents/web/components/SettingsDropdown.tsx
```

- [ ] **Step 4: Replace web/app/settings/page.tsx**

Replace the contents of `web/app/settings/page.tsx` with:

```tsx
import { redirect } from 'next/navigation'

export default function SettingsPage() {
  redirect('/')
}
```

- [ ] **Step 5: Build**

```bash
cd /Users/joehe/workspace/projects/pitagents/web
npm run build 2>&1 | tail -20
```

Expected: clean build. If TypeScript errors, they'll point to import references to the deleted SettingsDropdown or old settings page — fix any remaining imports.

- [ ] **Step 6: Commit**

```bash
cd /Users/joehe/workspace/projects/pitagents
git add web/components/settings/sections/AgentsSection.tsx web/components/settings/SettingsPanel.tsx web/app/settings/page.tsx
git rm web/components/SettingsDropdown.tsx
git commit -m "feat(web): add AgentsSection; remove SettingsDropdown; redirect /settings to /"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|---|---|
| Avatar click opens slide-in panel | Task 5 |
| 7 sections with sidebar nav | Task 5 |
| Account: display name, email (read-only), change password | Task 6 |
| Auth switched to DB-backed login | Task 1 |
| GET /auth/me, PATCH /auth/profile, PATCH /auth/password | Task 1 |
| Shop Profile: name, address, labor rate | Task 7 |
| GET/PATCH /settings/profile | Task 3 |
| Appearance: accent color + background theme | Task 7 |
| Booking: hours, slot duration, link | Task 8 |
| GET/PATCH /appointments/my-config | Task 2 |
| Notifications: service reminder configs | Task 8 |
| Integrations: 6 services with status badges | Task 9 |
| ShopSettingsResponse expanded with integration fields | Task 3 |
| Agents & AI: full CRUD | Task 10 |
| SettingsDropdown deleted | Task 10 |
| /settings page redirects to / | Task 10 |
| Panel overlay closes on click | Task 5 |
| × close button | Task 5 |
| Sign out in sidebar | Task 5 |

All spec requirements covered. ✓

**Type consistency check:**
- `UserProfile` defined in types.ts (Task 4), used in `getMe` / `updateProfile` (Task 4), consumed in `AccountSection` (Task 6) ✓
- `ShopProfile` defined in types.ts (Task 4), used in `getShopProfile` / `updateShopProfile` (Task 4), consumed in `ShopProfileSection` (Task 7) ✓
- `ShopSettings` expanded in types.ts (Task 4), matches expanded `ShopSettingsResponse` from Task 3 ✓
- `BookingConfig` already in types.ts, used by `getMyBookingConfig` (Task 4), consumed in `BookingSection` (Task 8) ✓
