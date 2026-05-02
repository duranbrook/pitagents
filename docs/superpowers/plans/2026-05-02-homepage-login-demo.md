# Homepage, Login & Request Demo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public marketing homepage, update the login page with Google OAuth, and add a /demo request page.

**Architecture:** `/` becomes a static marketing page; the existing dashboard moves to `/dashboard`. Google OAuth adds a `POST /auth/google` backend endpoint that verifies Google ID tokens and returns the same JWT shape as email/password login. Demo requests are stored in a new `demo_requests` DB table via `POST /demo/request`.

**Tech Stack:** Next.js 16 (App Router), React 19, Tailwind CSS 4, FastAPI, SQLAlchemy async, Alembic, `google-auth` Python package, Google Identity Services JS SDK.

**Visual reference mockups:** `.superpowers/brainstorm/49676-1777747077/content/` — `homepage-v2.html`, `login-page.html`, `demo-page.html`

---

## File Map

**Create:**
- `web/app/dashboard/page.tsx` — moves DashboardPage here (from `/`)
- `web/components/home/HomePage.tsx` — full marketing homepage component
- `web/app/demo/page.tsx` — request demo page
- `backend/src/models/demo_request.py` — DemoRequest SQLAlchemy model
- `backend/src/api/demo.py` — POST /demo/request endpoint
- `backend/alembic/versions/0026_google_oauth_and_demo_requests.py` — DB migration

**Modify:**
- `web/app/page.tsx` — replace dashboard render with `<HomePage />`
- `web/app/login/page.tsx` — add Google OAuth button + two-panel layout
- `backend/src/models/user.py` — add `google_id` column, make `hashed_password` nullable
- `backend/src/api/auth.py` — add `POST /auth/google` endpoint
- `backend/src/api/main.py` — register demo router
- `backend/src/config.py` — add `GOOGLE_CLIENT_ID` setting
- `backend/pyproject.toml` — add `google-auth` dependency

---

## Task 1: Move dashboard from `/` to `/dashboard`

**Files:**
- Create: `web/app/dashboard/page.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Create `/dashboard` page**

```tsx
// web/app/dashboard/page.tsx
import { DashboardPage } from '@/components/dashboard/DashboardPage'

export default function Dashboard() {
  return <DashboardPage />
}
```

- [ ] **Step 2: Clear out the root page (temporary — homepage goes in Task 8)**

```tsx
// web/app/page.tsx
export default function Home() {
  return <div />
}
```

- [ ] **Step 3: Update any internal links that pointed to `/`**

Search for links pointing to `/` that should now go to `/dashboard`:

```bash
grep -r 'href="/"' web/components web/app --include="*.tsx" | grep -v node_modules
```

Update any that are internal nav links pointing to the dashboard (not external or logo links).

- [ ] **Step 4: Verify the dashboard still loads**

```bash
cd web && npm run dev
```

Open `http://localhost:3000/dashboard` and confirm the dashboard renders. Open `http://localhost:3000` and confirm it shows a blank page (not the dashboard).

- [ ] **Step 5: Commit**

```bash
git add web/app/dashboard/page.tsx web/app/page.tsx
git commit -m "feat(web): move dashboard to /dashboard, clear root route"
```

---

## Task 2: Add `google-auth` to backend

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/src/config.py`

- [ ] **Step 1: Add `google-auth` to pyproject.toml**

In `backend/pyproject.toml`, add to the `dependencies` list:

```toml
"google-auth>=2.29.0",
```

- [ ] **Step 2: Install the dependency**

```bash
cd backend && pip install google-auth
```

Expected: installs `google-auth` and its dependency `cachetools`.

- [ ] **Step 3: Add `GOOGLE_CLIENT_ID` to config**

In `backend/src/config.py`, add after the `JWT_EXPIRE_MINUTES` line:

```python
GOOGLE_CLIENT_ID: str = ""
```

- [ ] **Step 4: Verify import works**

```bash
cd backend && python -c "from google.oauth2 import id_token; print('ok')"
```

Expected: prints `ok`.

- [ ] **Step 5: Commit**

```bash
git add backend/pyproject.toml backend/src/config.py
git commit -m "chore(backend): add google-auth dependency and GOOGLE_CLIENT_ID config"
```

---

## Task 3: DB migration — google_id on users + demo_requests table

**Files:**
- Modify: `backend/src/models/user.py`
- Create: `backend/alembic/versions/0026_google_oauth_and_demo_requests.py`

- [ ] **Step 1: Update User model**

Replace the full content of `backend/src/models/user.py`:

```python
import uuid
from sqlalchemy import Column, String, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id = Column(UUID(as_uuid=True), ForeignKey("shops.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # nullable for Google OAuth users
    google_id = Column(String(255), unique=True, nullable=True, index=True)
    role = Column(
        SAEnum("owner", "technician", name="user_role_enum"),
        nullable=False,
    )
    name = Column(String(255), nullable=True)
    preferences = Column(JSONB, nullable=False, server_default="{}")
```

- [ ] **Step 2: Create DemoRequest model**

```python
# backend/src/models/demo_request.py
import uuid
from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from src.db.base import Base


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    shop_name = Column(String(255), nullable=False)
    locations = Column(String(50), nullable=False)
    message = Column(String(2000), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

- [ ] **Step 3: Create Alembic migration**

```python
# backend/alembic/versions/0026_google_oauth_and_demo_requests.py
"""add google_id to users and create demo_requests table

Revision ID: 0026
Revises: 0025
Create Date: 2026-05-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make hashed_password nullable (Google OAuth users have no password)
    op.alter_column("users", "hashed_password", nullable=True)

    # Add google_id for Google OAuth identity linking
    op.add_column("users", sa.Column("google_id", sa.String(255), nullable=True))
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)

    # Demo requests table
    op.create_table(
        "demo_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(255), nullable=False),
        sa.Column("last_name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("shop_name", sa.String(255), nullable=False),
        sa.Column("locations", sa.String(50), nullable=False),
        sa.Column("message", sa.String(2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_demo_requests_email", "demo_requests", ["email"])


def downgrade() -> None:
    op.drop_index("ix_demo_requests_email", table_name="demo_requests")
    op.drop_table("demo_requests")
    op.drop_index("ix_users_google_id", table_name="users")
    op.drop_column("users", "google_id")
    op.alter_column("users", "hashed_password", nullable=False)
```

- [ ] **Step 4: Run migration against local DB**

```bash
cd backend && alembic upgrade head
```

Expected: `Running upgrade 0025 -> 0026, add google_id to users and create demo_requests table`

- [ ] **Step 5: Commit**

```bash
git add backend/src/models/user.py backend/src/models/demo_request.py \
        backend/alembic/versions/0026_google_oauth_and_demo_requests.py
git commit -m "feat(backend): add google_id to users, create demo_requests table"
```

---

## Task 4: Backend — POST /auth/google endpoint

**Files:**
- Modify: `backend/src/api/auth.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_google_auth.py
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock
from src.api.main import app


@pytest.mark.asyncio
async def test_google_login_valid_token(db_session, test_user):
    """Valid Google token for existing user returns JWT."""
    mock_idinfo = {
        "sub": "google-sub-123",
        "email": test_user.email,
        "email_verified": True,
    }
    with patch("src.api.auth.id_token.verify_oauth2_token", return_value=mock_idinfo):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_google_login_unknown_email(db_session):
    """Google token for unknown email returns 401."""
    mock_idinfo = {
        "sub": "google-sub-999",
        "email": "nobody@example.com",
        "email_verified": True,
    }
    with patch("src.api.auth.id_token.verify_oauth2_token", return_value=mock_idinfo):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/auth/google", json={"id_token": "fake-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_google_login_invalid_token(db_session):
    """Invalid Google token returns 401."""
    with patch("src.api.auth.id_token.verify_oauth2_token", side_effect=ValueError("bad token")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post("/auth/google", json={"id_token": "bad-token"})
    assert resp.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_api/test_google_auth.py -v
```

Expected: FAIL — `ImportError` or `404` (endpoint doesn't exist yet).

- [ ] **Step 3: Add the endpoint to auth.py**

Add these imports at the top of `backend/src/api/auth.py`:

```python
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
```

Add this Pydantic model after the existing models:

```python
class GoogleLoginRequest(BaseModel):
    id_token: str
```

Add this endpoint after the existing `login` endpoint:

```python
@router.post("/google", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        idinfo = id_token.verify_oauth2_token(
            request.id_token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID or None,  # None skips audience check (dev only)
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token")

    google_sub = idinfo["sub"]
    email = idinfo.get("email", "")

    # Find by google_id first (returning user), then fall back to email
    result = await db.execute(select(User).where(User.google_id == google_sub))
    user = result.scalar_one_or_none()

    if user is None:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No account found. Request a demo to get access.",
            )
        # Link google_id for future logins
        user.google_id = google_sub
        await db.commit()

    token = create_access_token({
        "sub": str(user.id),
        "shop_id": str(user.shop_id),
        "role": user.role,
        "email": user.email,
    })
    return TokenResponse(access_token=token)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_api/test_google_auth.py -v
```

Expected: all 3 tests PASS. (The `db_session` and `test_user` fixtures may need to be checked against `tests/conftest.py` — if they don't exist, check what fixtures the existing auth tests use and replicate the pattern.)

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/auth.py backend/tests/test_api/test_google_auth.py
git commit -m "feat(backend): add POST /auth/google endpoint for Google OAuth"
```

---

## Task 5: Backend — demo request endpoint

**Files:**
- Create: `backend/src/api/demo.py`
- Modify: `backend/src/api/main.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api/test_demo.py
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.mark.asyncio
async def test_submit_demo_request(db_session):
    """Valid demo request returns ok: true."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/demo/request", json={
            "first_name": "Marcus",
            "last_name": "Thompson",
            "email": "marcus@cityauto.com",
            "shop_name": "City Auto Center",
            "locations": "1 location",
            "message": "Looking forward to the demo.",
        })
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_submit_demo_request_missing_field(db_session):
    """Missing required field returns 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/demo/request", json={
            "first_name": "Marcus",
            # missing last_name, email, shop_name, locations
        })
    assert resp.status_code == 422
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && pytest tests/test_api/test_demo.py -v
```

Expected: FAIL — `404` (endpoint doesn't exist yet).

- [ ] **Step 3: Create the demo router**

```python
# backend/src/api/demo.py
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.base import get_db
from src.models.demo_request import DemoRequest

router = APIRouter(prefix="/demo", tags=["demo"])


class DemoRequestBody(BaseModel):
    first_name: str
    last_name: str
    email: str
    shop_name: str
    locations: str
    message: Optional[str] = None


class OkResponse(BaseModel):
    ok: bool = True


@router.post("/request", response_model=OkResponse)
async def submit_demo_request(
    body: DemoRequestBody,
    db: AsyncSession = Depends(get_db),
) -> OkResponse:
    record = DemoRequest(
        id=uuid.uuid4(),
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        shop_name=body.shop_name,
        locations=body.locations,
        message=body.message,
    )
    db.add(record)
    await db.commit()
    return OkResponse()
```

- [ ] **Step 4: Register the router in main.py**

Add to `backend/src/api/main.py`, after the other imports:

```python
from src.api.demo import router as demo_router
```

And in the router registration section:

```python
app.include_router(demo_router)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && pytest tests/test_api/test_demo.py -v
```

Expected: both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api/demo.py backend/src/api/main.py \
        backend/tests/test_api/test_demo.py
git commit -m "feat(backend): add POST /demo/request endpoint"
```

---

## Task 6: Frontend — Homepage

**Files:**
- Create: `web/components/home/HomePage.tsx`
- Modify: `web/app/page.tsx`

- [ ] **Step 1: Create the HomePage component**

Create `web/components/home/HomePage.tsx`. This is a large static component — translate the approved mockup at `.superpowers/brainstorm/49676-1777747077/content/homepage-v2.html` directly into React/TSX. Key conversion rules:
- `class=` → `className=`
- `onclick=` → `onClick=`
- Self-closing tags (`<hr />`, `<input />`)
- CSS `background-clip: text` needs `-webkit-background-clip` + `-webkit-text-fill-color` as inline styles (Tailwind can't do gradient text without arbitrary values)
- `href="#"` anchor links stay as-is for now (scroll behavior can be added later)

The full component:

```tsx
// web/components/home/HomePage.tsx
'use client'

import Link from 'next/link'

export function HomePage() {
  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", background: '#fff', color: '#0f172a' }}>

      {/* NAV */}
      <nav style={{
        background: 'rgba(255,255,255,0.92)',
        backdropFilter: 'blur(12px)',
        WebkitBackdropFilter: 'blur(12px)',
        borderBottom: '1px solid #f1f5f9',
        padding: '0 64px',
        height: 62,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        position: 'sticky',
        top: 0,
        zIndex: 100,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontWeight: 800, fontSize: 15, color: '#0f172a', letterSpacing: -0.3 }}>
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14, boxShadow: '0 2px 8px rgba(37,99,235,0.3)' }}>A</div>
          AutoShop
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32 }}>
          <a href="#product" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Product</a>
          <a href="#pricing" style={{ fontSize: 13.5, color: '#64748b', textDecoration: 'none', fontWeight: 500 }}>Pricing</a>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Link href="/login" style={{ fontSize: 13.5, color: '#64748b', fontWeight: 500, textDecoration: 'none' }}>Sign In</Link>
          <Link href="/demo" style={{
            background: '#2563eb', color: '#fff', padding: '8px 18px',
            borderRadius: 8, fontSize: 13.5, fontWeight: 600,
            boxShadow: '0 1px 4px rgba(37,99,235,0.25)', textDecoration: 'none',
          }}>Request Demo</Link>
        </div>
      </nav>

      {/* HERO */}
      <section style={{
        background: 'linear-gradient(160deg, #f0f7ff 0%, #ffffff 50%, #f8faff 100%)',
        padding: '100px 64px 80px',
        textAlign: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute', top: -120, left: '50%', transform: 'translateX(-50%)',
          width: 700, height: 700,
          background: 'radial-gradient(circle, rgba(37,99,235,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        {/* Badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          background: '#fff', border: '1px solid #e2e8f0',
          color: '#475569', fontSize: 12, fontWeight: 600,
          padding: '5px 14px', borderRadius: 99, marginBottom: 28,
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
        }}>
          <span style={{ width: 6, height: 6, background: '#22c55e', borderRadius: '50%', display: 'inline-block' }} />
          Now live for independent auto shops
        </div>

        {/* Headline */}
        <h1 style={{ fontSize: 58, fontWeight: 900, lineHeight: 1.08, color: '#0f172a', maxWidth: 720, margin: '0 auto 22px', letterSpacing: -2 }}>
          Give your shop{' '}
          <em style={{
            fontStyle: 'normal',
            background: 'linear-gradient(135deg, #2563eb, #7c3aed)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
          }}>AI superpowers</em>
        </h1>
        <p style={{ fontSize: 18, color: '#64748b', maxWidth: 520, margin: '0 auto 40px', lineHeight: 1.65 }}>
          Automate inspections, empower technicians, and keep every customer connected — across every shop they visit.
        </p>

        {/* CTAs */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'center', alignItems: 'center', marginBottom: 60 }}>
          <Link href="/demo" style={{
            background: '#2563eb', color: '#fff', padding: '13px 28px',
            borderRadius: 9, fontSize: 15, fontWeight: 700,
            boxShadow: '0 4px 14px rgba(37,99,235,0.35)', textDecoration: 'none',
          }}>Request a Demo</Link>
          <Link href="/login" style={{
            color: '#475569', fontSize: 15, fontWeight: 500,
            background: 'none', border: '1.5px solid #e2e8f0',
            borderRadius: 9, padding: '12px 22px', textDecoration: 'none',
          }}>Sign in →</Link>
        </div>

        {/* Product preview */}
        <div style={{
          maxWidth: 860, margin: '0 auto',
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: 14, overflow: 'hidden',
          boxShadow: '0 20px 60px rgba(0,0,0,0.10), 0 4px 16px rgba(0,0,0,0.06)',
        }}>
          {/* Browser chrome */}
          <div style={{ background: '#f8fafc', borderBottom: '1px solid #e2e8f0', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#f87171', display: 'inline-block' }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#fbbf24', display: 'inline-block' }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#4ade80', display: 'inline-block' }} />
            <div style={{ flex: 1, background: '#f1f5f9', borderRadius: 4, height: 14, marginLeft: 10 }} />
          </div>
          {/* App preview */}
          <div style={{ display: 'grid', gridTemplateColumns: '200px 1fr', minHeight: 260 }}>
            {/* Sidebar */}
            <div style={{ background: '#0f172a', padding: '20px 16px' }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'rgba(255,255,255,0.3)', letterSpacing: 1, padding: '0 10px 12px' }}>AUTOSHOP</div>
              {[
                { label: 'Dashboard', active: true },
                { label: 'Chat', active: false },
                { label: 'Inspections', active: false },
                { label: 'Job Cards', active: false },
                { label: 'Customers', active: false },
                { label: 'Reports', active: false },
              ].map(item => (
                <div key={item.label} style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '7px 10px', borderRadius: 7, fontSize: 11,
                  color: item.active ? '#fff' : 'rgba(255,255,255,0.5)',
                  background: item.active ? 'rgba(255,255,255,0.08)' : 'transparent',
                  fontWeight: item.active ? 600 : 400,
                  marginBottom: 2,
                }}>
                  <div style={{ width: 14, height: 14, borderRadius: 3, background: item.active ? '#2563eb' : 'rgba(255,255,255,0.15)' }} />
                  {item.label}
                </div>
              ))}
            </div>
            {/* Main content */}
            <div style={{ padding: '20px 24px' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#0f172a', marginBottom: 14 }}>Good morning, Marcus 👋</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, marginBottom: 16 }}>
                {[
                  { val: '12', label: 'Open Jobs' },
                  { val: '$8.4k', label: 'Revenue today' },
                  { val: '94%', label: 'Satisfaction' },
                ].map(stat => (
                  <div key={stat.label} style={{ background: '#f8fafc', border: '1px solid #f1f5f9', borderRadius: 8, padding: '10px 12px' }}>
                    <div style={{ fontSize: 18, fontWeight: 800, color: '#0f172a', marginBottom: 2 }}>{stat.val}</div>
                    <div style={{ fontSize: 9, color: '#94a3b8', fontWeight: 500 }}>{stat.label}</div>
                  </div>
                ))}
              </div>
              <div style={{ background: '#f8fafc', borderRadius: 8, padding: '12px 14px', border: '1px solid #f1f5f9' }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: '#64748b', marginBottom: 8 }}>Ask your AI →</div>
                <div style={{ fontSize: 10, color: '#475569', padding: '6px 10px', background: '#fff', borderRadius: 6, border: '1px solid #f1f5f9', marginBottom: 6 }}>What&apos;s our top repair this week?</div>
                <div style={{ fontSize: 10, color: '#fff', padding: '6px 10px', background: '#2563eb', borderRadius: 6, display: 'inline-block' }}>Brake service — 7 jobs, $3,220 revenue. Up 18% vs last week.</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* METRICS BAND */}
      <div style={{ background: '#0f172a', padding: '40px 64px', display: 'flex', justifyContent: 'center', gap: 80 }}>
        {[
          { val: '2×', label: 'Faster inspections' },
          { val: '40% less admin', label: 'Per technician daily' },
          { val: '100%', label: 'Repair history coverage' },
          { val: '$0', label: 'For your customers' },
        ].map(m => (
          <div key={m.label} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 36, fontWeight: 900, color: '#60a5fa', letterSpacing: -1 }}>{m.val}</div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 4, fontWeight: 500, textTransform: 'uppercase', letterSpacing: 1 }}>{m.label}</div>
          </div>
        ))}
      </div>

      {/* PRODUCT SECTION */}
      <section id="product" style={{ padding: '96px 64px', background: '#fff' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#2563eb', textTransform: 'uppercase', marginBottom: 12 }}>Product</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>Built for every role<br />in your shop</h2>
          <p style={{ fontSize: 16, color: '#64748b', maxWidth: 480, lineHeight: 1.65, marginBottom: 56 }}>From the owner&apos;s chair to the technician&apos;s bay — everyone gets the right AI at the right moment.</p>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

            {/* Owner */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '24px 24px 0', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150 }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 8 }}>
                  {[{ n: '$24k', l: 'Monthly Rev' }, { n: '47', l: 'Jobs Done' }, { n: '98%', l: 'Satisfaction' }].map(s => (
                    <div key={s.l} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 10 }}>
                      <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{s.n}</div>
                      <div style={{ fontSize: 9, color: '#94a3b8' }}>{s.l}</div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>📊</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Owner Intelligence</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Ask any question about your shop — revenue, team performance, job status — and get instant answers. AI agents with full visibility across every department.</p>
              </div>
            </div>

            {/* Technician */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '24px 24px 16px', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150 }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <div style={{ fontSize: 10, padding: '7px 10px', borderRadius: 8, background: '#eff6ff', color: '#1d4ed8', alignSelf: 'flex-end', maxWidth: '90%' }}>Customer says the brakes squeal at low speed.</div>
                  <div style={{ fontSize: 10, padding: '7px 10px', borderRadius: 8, background: '#fff', border: '1px solid #e2e8f0', color: '#0f172a', maxWidth: '90%' }}>Likely glazed pads or worn rotors. Check pad thickness — if under 3mm, recommend replacement. I&apos;ll draft the repair note.</div>
                </div>
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#f0fdf4', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🔧</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>AI Technician Assistant</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Every technician gets a dedicated AI co-pilot. It guides inspections, drafts repair notes, looks up parts, and handles the paperwork — so they can stay under the hood.</p>
              </div>
            </div>

            {/* Consumer */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '16px 24px 0', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150 }}>
                {[
                  { shop: 'City Auto Center', repair: 'Brake pad replacement + rotor resurface', date: 'Mar 2026' },
                  { shop: 'QuickLube Express', repair: 'Oil change + tire rotation', date: 'Jan 2026' },
                  { shop: 'Downtown Motors', repair: 'AC recharge + cabin filter', date: 'Nov 2025' },
                ].map(r => (
                  <div key={r.shop} style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 7, padding: '8px 10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 600, color: '#0f172a' }}>{r.shop}</div>
                      <div style={{ fontSize: 9, color: '#64748b', marginTop: 1 }}>{r.repair}</div>
                    </div>
                    <div style={{ fontSize: 9, color: '#94a3b8' }}>{r.date}</div>
                  </div>
                ))}
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#fdf4ff', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🚗</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Consumer Vehicle History</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Customers see their complete repair history across every shop they&apos;ve ever visited. One timeline. Every vehicle. Every repair — no more lost records.</p>
              </div>
            </div>

            {/* Ecosystem */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: '#fff' }}>
              <div style={{ padding: '32px 24px 0', background: '#f8fafc', borderBottom: '1px solid #f1f5f9', minHeight: 150, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 8, alignItems: 'center', textAlign: 'center', width: '100%' }}>
                  <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: 8, fontSize: 9, fontWeight: 600, color: '#1d4ed8' }}>Shop Owner</div>
                  <div style={{ fontSize: 14, color: '#cbd5e1' }}>⇄</div>
                  <div style={{ background: '#eff6ff', border: '1px solid #bfdbfe', borderRadius: 8, padding: 8, fontSize: 9, fontWeight: 600, color: '#1d4ed8' }}>Technician</div>
                  <div style={{ gridColumn: '1/-1', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, marginTop: 4 }}>
                    <span style={{ fontSize: 9, color: '#94a3b8' }}>connected via</span>
                    <span style={{ fontSize: 10, fontWeight: 700, color: '#2563eb' }}>AutoShop Platform</span>
                  </div>
                  <div style={{ gridColumn: 2, background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: 8, fontSize: 9, fontWeight: 600, color: '#475569' }}>Consumer</div>
                </div>
              </div>
              <div style={{ padding: '22px 24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
                  <div style={{ width: 32, height: 32, borderRadius: 8, background: '#fff7ed', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 15 }}>🔗</div>
                  <div style={{ fontSize: 16, fontWeight: 800, color: '#0f172a' }}>Connected Ecosystem</div>
                </div>
                <p style={{ fontSize: 13, color: '#64748b', lineHeight: 1.65 }}>Shops, technicians, and customers all on one platform. Records, updates, and repair history flow seamlessly between every party in the repair lifecycle.</p>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* WHY SECTION */}
      <section style={{ background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)', padding: '96px 64px' }}>
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#60a5fa', textTransform: 'uppercase', marginBottom: 12 }}>Why AutoShop</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#f8fafc', letterSpacing: -1, lineHeight: 1.1, marginBottom: 12 }}>AI that works for the<br />whole automotive world</h2>
          <p style={{ fontSize: 16, color: 'rgba(255,255,255,0.45)', maxWidth: 480, lineHeight: 1.65, marginBottom: 48 }}>Two transformations. One platform.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
            {[
              { num: '01', title: 'Superpower every shop', body: 'AutoShop brings enterprise-grade AI to independent auto shops. Automate quotes, inspections, scheduling, and reporting — without adding headcount.' },
              { num: '02', title: 'Connect every consumer', body: "For the first time, customers can access their complete repair history across every shop they've used. One timeline. Every vehicle. Every repair." },
            ].map(card => (
              <div key={card.num} style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 16, padding: 36 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: '#3b82f6', letterSpacing: 2, marginBottom: 16 }}>{card.num}</div>
                <h3 style={{ fontSize: 22, fontWeight: 800, color: '#f1f5f9', marginBottom: 12, letterSpacing: -0.3 }}>{card.title}</h3>
                <p style={{ fontSize: 14, color: 'rgba(255,255,255,0.5)', lineHeight: 1.75 }}>{card.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* TESTIMONIAL */}
      <section style={{ background: '#f8fafc', padding: '80px 64px' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', textAlign: 'center' }}>
          <div style={{ fontSize: 64, lineHeight: 1, color: '#e2e8f0', fontFamily: 'Georgia, serif', marginBottom: -10 }}>&ldquo;</div>
          <p style={{ fontSize: 22, fontWeight: 600, color: '#0f172a', lineHeight: 1.55, letterSpacing: -0.3, marginBottom: 28 }}>
            AutoShop cut our inspection write-up time in half. My technicians actually enjoy using it — and customers love seeing their full vehicle history in one place.
          </p>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg,#2563eb,#7c3aed)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 700, fontSize: 14 }}>M</div>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: '#0f172a' }}>Marcus T.</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>Owner, City Auto Center</div>
            </div>
          </div>
        </div>
      </section>

      {/* PRICING */}
      <section id="pricing" style={{ padding: '96px 64px', background: '#fff' }}>
        <div style={{ maxWidth: 980, margin: '0 auto' }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 2, color: '#2563eb', textTransform: 'uppercase', marginBottom: 12 }}>Pricing</div>
          <h2 style={{ fontSize: 40, fontWeight: 900, color: '#0f172a', letterSpacing: -1, lineHeight: 1.1, marginBottom: 14 }}>Simple, transparent pricing</h2>
          <p style={{ fontSize: 16, color: '#64748b', lineHeight: 1.65 }}>Start at $39/month. Scale when you&apos;re ready.</p>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginTop: 56 }}>

            {/* Starter */}
            <div style={{ border: '2px solid #2563eb', borderRadius: 20, padding: 36, boxShadow: '0 4px 24px rgba(37,99,235,0.1)' }}>
              <div style={{ display: 'inline-block', background: '#eff6ff', color: '#2563eb', fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' as const }}>Starter</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>Single Shop</div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>Everything you need to run one location with AI.</p>
              <div style={{ fontSize: 52, fontWeight: 900, color: '#0f172a', letterSpacing: -2, lineHeight: 1, marginBottom: 4 }}>
                <sup style={{ fontSize: 24, letterSpacing: 0, verticalAlign: 'super' }}>$</sup>39<sub style={{ fontSize: 14, fontWeight: 400, color: '#94a3b8', letterSpacing: 0, verticalAlign: 'baseline' }}>/month</sub>
              </div>
              <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
              {['1 shop location', 'Up to 5 staff accounts', 'AI Technician Assistant', 'Owner Intelligence Dashboard', 'Consumer vehicle history'].map(f => (
                <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#2563eb', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
                </div>
              ))}
              <Link href="/login" style={{
                display: 'block', width: '100%', marginTop: 32, padding: 13,
                borderRadius: 10, fontSize: 14, fontWeight: 700, textAlign: 'center',
                background: '#2563eb', color: '#fff',
                boxShadow: '0 2px 8px rgba(37,99,235,0.3)', textDecoration: 'none',
              }}>Get started</Link>
            </div>

            {/* Enterprise */}
            <div style={{ border: '1px solid #e2e8f0', borderRadius: 20, padding: 36 }}>
              <div style={{ display: 'inline-block', background: '#f8fafc', color: '#64748b', fontSize: 10, fontWeight: 700, padding: '4px 12px', borderRadius: 99, marginBottom: 20, letterSpacing: 1, textTransform: 'uppercase' as const }}>Enterprise</div>
              <div style={{ fontSize: 22, fontWeight: 800, color: '#0f172a', marginBottom: 6 }}>Multi-Location</div>
              <p style={{ fontSize: 13, color: '#94a3b8', marginBottom: 28, lineHeight: 1.5 }}>Custom pricing for groups, chains, and dealerships.</p>
              <div style={{ fontSize: 32, fontWeight: 900, color: '#2563eb', letterSpacing: -0.5, lineHeight: 1, marginBottom: 4 }}>Let&apos;s talk</div>
              <hr style={{ border: 'none', borderTop: '1px solid #f1f5f9', margin: '24px 0' }} />
              {['Multiple shop locations', 'Unlimited staff accounts', 'Everything in Starter', 'Priority support & onboarding', 'Custom integrations (DMS, fleet)'].map(f => (
                <div key={f} style={{ fontSize: 13, color: '#475569', padding: '6px 0', display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                  <span style={{ color: '#2563eb', fontWeight: 700, flexShrink: 0 }}>✓</span> {f}
                </div>
              ))}
              <Link href="/demo" style={{
                display: 'block', width: '100%', marginTop: 32, padding: 13,
                borderRadius: 10, fontSize: 14, fontWeight: 700, textAlign: 'center',
                background: '#fff', color: '#0f172a',
                border: '1.5px solid #e2e8f0', textDecoration: 'none',
              }}>Request a Demo →</Link>
            </div>

          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer style={{ background: '#0f172a', padding: '40px 64px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700, fontSize: 14, color: '#fff' }}>
          <div style={{ width: 24, height: 24, background: 'linear-gradient(135deg,#2563eb,#1d4ed8)', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 11 }}>A</div>
          AutoShop
        </div>
        <div style={{ display: 'flex', gap: 24 }}>
          {['Privacy', 'Terms', 'Contact'].map(l => (
            <a key={l} href="#" style={{ fontSize: 12, color: 'rgba(255,255,255,0.35)', textDecoration: 'none' }}>{l}</a>
          ))}
        </div>
        <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.3)' }}>© 2026 AutoShop. All rights reserved.</div>
      </footer>

    </div>
  )
}
```

- [ ] **Step 2: Update web/app/page.tsx**

```tsx
// web/app/page.tsx
import { HomePage } from '@/components/home/HomePage'

export default function Home() {
  return <HomePage />
}
```

- [ ] **Step 3: Start dev server and verify the homepage renders**

```bash
cd web && npm run dev
```

Open `http://localhost:3000`. Scroll through the full page — nav, hero with product preview, metrics band, 4 feature cards, why section, testimonial, pricing, footer. All should render without errors.

- [ ] **Step 4: Commit**

```bash
git add web/components/home/HomePage.tsx web/app/page.tsx
git commit -m "feat(web): add marketing homepage at /"
```

---

## Task 7: Frontend — Login page with Google OAuth

**Files:**
- Modify: `web/app/login/page.tsx`

- [ ] **Step 1: Replace login/page.tsx with the two-panel Google OAuth design**

```tsx
// web/app/login/page.tsx
'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import Script from 'next/script'
import Link from 'next/link'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: object) => void
          renderButton: (element: HTMLElement, config: object) => void
        }
      }
    }
  }
}

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const googleBtnRef = useRef<HTMLDivElement>(null)

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  function initGoogle() {
    if (!window.google || !googleBtnRef.current) return
    window.google.accounts.id.initialize({
      client_id: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || '',
      callback: handleGoogleCredential,
    })
    window.google.accounts.id.renderButton(googleBtnRef.current, {
      theme: 'outline',
      size: 'large',
      width: 380,
      text: 'continue_with',
    })
  }

  async function handleGoogleCredential(response: { credential: string }) {
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: response.credential }),
      })
      if (!res.ok) {
        const data = await res.json()
        setError(data.detail || 'Google sign-in failed')
        setLoading(false)
        return
      }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      router.push('/chat')
    } catch {
      setError('Could not connect to server')
      setLoading(false)
    }
  }

  async function handleEmailSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    let navigated = false
    try {
      const res = await fetch(`${API}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!res.ok) { setError('Invalid email or password'); return }
      const data = await res.json()
      localStorage.setItem('token', data.access_token)
      navigated = true
      router.push('/chat')
    } catch {
      setError('Could not connect to server')
    } finally {
      if (!navigated) setLoading(false)
    }
  }

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        onLoad={initGoogle}
        strategy="afterInteractive"
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: '100vh', fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif" }}>

        {/* LEFT */}
        <div style={{
          background: 'linear-gradient(160deg, #0f172a 0%, #1e3a5f 100%)',
          padding: '60px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          position: 'relative',
          overflow: 'hidden',
        }}>
          <div style={{ position: 'absolute', bottom: -100, right: -100, width: 400, height: 400, background: 'radial-gradient(circle, rgba(37,99,235,0.25) 0%, transparent 70%)', pointerEvents: 'none' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 34, height: 34, background: 'linear-gradient(135deg,#2563eb,#1d4ed8)', borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 900, fontSize: 16 }}>A</div>
            <span style={{ fontSize: 17, fontWeight: 800, color: '#fff', letterSpacing: -0.3 }}>AutoShop</span>
          </div>

          <div style={{ position: 'relative', zIndex: 1 }}>
            <h1 style={{ fontSize: 36, fontWeight: 900, color: '#fff', lineHeight: 1.15, letterSpacing: -1, marginBottom: 16 }}>
              Your shop&apos;s{' '}
              <em style={{ fontStyle: 'normal', color: '#60a5fa' }}>AI team</em>
              <br />is waiting.
            </h1>
            <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.45)', lineHeight: 1.65, maxWidth: 340 }}>
              Sign in to access your owner dashboard, AI technician assistant, and full shop intelligence — in one place.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 32, position: 'relative', zIndex: 1 }}>
            {[{ val: '2×', label: 'Faster inspections' }, { val: '40%', label: 'Less admin' }, { val: '$0', label: 'For customers' }].map(s => (
              <div key={s.label}>
                <div style={{ fontSize: 22, fontWeight: 900, color: '#fff' }}>{s.val}</div>
                <div style={{ fontSize: 11, color: 'rgba(255,255,255,0.4)', marginTop: 2 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ background: '#fff', padding: '60px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ maxWidth: 380, width: '100%', margin: '0 auto' }}>
            <h2 style={{ fontSize: 26, fontWeight: 900, color: '#0f172a', letterSpacing: -0.5, marginBottom: 6 }}>Sign in</h2>
            <p style={{ fontSize: 14, color: '#64748b', marginBottom: 32 }}>Welcome back. Sign in to your shop account.</p>

            {/* Google button container — renderButton writes into this div */}
            <div ref={googleBtnRef} style={{ marginBottom: 20 }} />

            {/* Divider */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <div style={{ flex: 1, borderTop: '1px solid #f1f5f9' }} />
              <span style={{ fontSize: 12, color: '#94a3b8', fontWeight: 500, whiteSpace: 'nowrap' }}>or sign in with email</span>
              <div style={{ flex: 1, borderTop: '1px solid #f1f5f9' }} />
            </div>

            <form onSubmit={handleEmailSubmit}>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Email</label>
                <input
                  type="email" value={email} onChange={e => setEmail(e.target.value)} required
                  placeholder="you@yourshop.com"
                  style={{ width: '100%', padding: '10px 14px', background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 9, fontSize: 14, color: '#0f172a', outline: 'none', boxSizing: 'border-box' }}
                  onFocus={e => (e.target.style.borderColor = '#2563eb')}
                  onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
                />
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6 }}>Password</label>
                <input
                  type="password" value={password} onChange={e => setPassword(e.target.value)} required
                  placeholder="••••••••"
                  style={{ width: '100%', padding: '10px 14px', background: '#f8fafc', border: '1.5px solid #e2e8f0', borderRadius: 9, fontSize: 14, color: '#0f172a', outline: 'none', boxSizing: 'border-box' }}
                  onFocus={e => (e.target.style.borderColor = '#2563eb')}
                  onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
                />
              </div>

              {error && <p style={{ fontSize: 13, color: '#ef4444', marginBottom: 12 }}>{error}</p>}

              <button
                type="submit" disabled={loading}
                style={{ width: '100%', padding: 12, background: loading ? '#93c5fd' : '#2563eb', color: '#fff', border: 'none', borderRadius: 10, fontSize: 14, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer', boxShadow: '0 2px 8px rgba(37,99,235,0.3)' }}
              >
                {loading ? 'Signing in…' : 'Sign in'}
              </button>
            </form>

            <p style={{ fontSize: 12, color: '#94a3b8', marginTop: 20, textAlign: 'center' }}>
              Don&apos;t have an account?{' '}
              <Link href="/demo" style={{ color: '#2563eb', fontWeight: 600, textDecoration: 'none' }}>Request a demo</Link>
            </p>
          </div>
        </div>

      </div>
    </>
  )
}
```

- [ ] **Step 2: Add NEXT_PUBLIC_GOOGLE_CLIENT_ID to web env**

Create or update `web/.env.local` (do not commit this file):

```
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

- [ ] **Step 3: Verify the login page renders**

Open `http://localhost:3000/login`. You should see the two-panel layout. The Google button container will be empty until `NEXT_PUBLIC_GOOGLE_CLIENT_ID` is set with a real client ID. The email/password form should work as before.

- [ ] **Step 4: Commit**

```bash
git add web/app/login/page.tsx
git commit -m "feat(web): update login page with Google OAuth and two-panel layout"
```

---

## Task 8: Frontend — Request Demo page

**Files:**
- Create: `web/app/demo/page.tsx`

- [ ] **Step 1: Create the demo page**

```tsx
// web/app/demo/page.tsx
'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function DemoPage() {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '',
    shop_name: '', locations: '', message: '',
  })
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState('')

  const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  function set(field: string, value: string) {
    setForm(f => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await fetch(`${API}/demo/request`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) { setError('Something went wrong. Please try again.'); return }
      setSubmitted(true)
    } catch {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '10px 14px',
    background: '#f8fafc', border: '1.5px solid #e2e8f0',
    borderRadius: 9, fontSize: 14, color: '#0f172a',
    outline: 'none', boxSizing: 'border-box', fontFamily: 'inherit',
  }
  const labelStyle: React.CSSProperties = {
    display: 'block', fontSize: 12.5, fontWeight: 600, color: '#374151', marginBottom: 6,
  }

  return (
    <div style={{ fontFamily: "-apple-system, BlinkMacSystemFont, 'Inter', 'Segoe UI', sans-serif", minHeight: '100vh', background: '#f8fafc' }}>

      {/* NAV */}
      <nav style={{ background: 'rgba(255,255,255,0.92)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)', borderBottom: '1px solid #f1f5f9', padding: '0 64px', height: 62, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontWeight: 800, fontSize: 15, color: '#0f172a' }}>
          <div style={{ width: 30, height: 30, background: 'linear-gradient(135deg, #2563eb, #1d4ed8)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff', fontWeight: 800, fontSize: 14 }}>A</div>
          AutoShop
        </div>
        <Link href="/" style={{ fontSize: 13, color: '#64748b', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>← Back to home</Link>
      </nav>

      {/* MAIN */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', minHeight: 'calc(100vh - 62px)' }}>

        {/* LEFT */}
        <div style={{ background: 'linear-gradient(160deg, #0f172a 0%, #1e3a5f 100%)', padding: '72px 64px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', bottom: -80, right: -80, width: 360, height: 360, background: 'radial-gradient(circle, rgba(37,99,235,0.2) 0%, transparent 70%)', pointerEvents: 'none' }} />
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: '#60a5fa', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 20 }}>Request a Demo</div>
            <h1 style={{ fontSize: 38, fontWeight: 900, color: '#fff', lineHeight: 1.12, letterSpacing: -1, marginBottom: 18 }}>
              See AutoShop{' '}
              <em style={{ fontStyle: 'normal', color: '#60a5fa' }}>in action</em>
            </h1>
            <p style={{ fontSize: 15, color: 'rgba(255,255,255,0.45)', lineHeight: 1.7, maxWidth: 360, marginBottom: 48 }}>
              We&apos;ll walk you through the full platform — owner dashboard, AI technician assistant, and consumer vehicle history. 30 minutes, no pressure.
            </p>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'rgba(255,255,255,0.3)', letterSpacing: 1.5, textTransform: 'uppercase', marginBottom: 16 }}>What to expect</div>
            {[
              { title: 'Live walkthrough', desc: 'of the owner dashboard and AI agents — using your shop\'s real workflow' },
              { title: 'AI Technician demo', desc: 'see how inspection reports are generated in seconds' },
              { title: 'Pricing & onboarding', desc: "we'll find the right plan and get you set up fast" },
              { title: 'Q&A', desc: 'ask anything, no sales script' },
            ].map(item => (
              <div key={item.title} style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 16 }}>
                <div style={{ width: 20, height: 20, borderRadius: '50%', background: 'rgba(37,99,235,0.3)', border: '1px solid rgba(37,99,235,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 }}>
                  <div style={{ width: 6, height: 6, background: '#60a5fa', borderRadius: '50%' }} />
                </div>
                <div style={{ fontSize: 13.5, color: 'rgba(255,255,255,0.6)', lineHeight: 1.5 }}>
                  <strong style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 600 }}>{item.title}</strong> — {item.desc}
                </div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.2)', position: 'relative', zIndex: 1 }}>Usually responds within 1 business day.</div>
        </div>

        {/* RIGHT */}
        <div style={{ background: '#fff', padding: '72px 64px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          {submitted ? (
            <div style={{ maxWidth: 400, textAlign: 'center' }}>
              <div style={{ fontSize: 48, marginBottom: 16 }}>🎉</div>
              <h2 style={{ fontSize: 24, fontWeight: 900, color: '#0f172a', marginBottom: 8 }}>We&apos;ll be in touch!</h2>
              <p style={{ fontSize: 15, color: '#64748b', lineHeight: 1.65 }}>Thanks for your interest. We&apos;ll reach out within 1 business day to schedule your demo.</p>
              <Link href="/" style={{ display: 'inline-block', marginTop: 24, fontSize: 14, color: '#2563eb', textDecoration: 'none', fontWeight: 600 }}>← Back to home</Link>
            </div>
          ) : (
            <div style={{ maxWidth: 400, width: '100%', margin: '0 auto' }}>
              <h2 style={{ fontSize: 26, fontWeight: 900, color: '#0f172a', letterSpacing: -0.5, marginBottom: 6 }}>Book your demo</h2>
              <p style={{ fontSize: 14, color: '#64748b', marginBottom: 32, lineHeight: 1.5 }}>Tell us a little about your shop and we&apos;ll be in touch shortly.</p>

              <form onSubmit={handleSubmit}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 18 }}>
                  <div>
                    <label style={labelStyle}>First name</label>
                    <input style={inputStyle} type="text" placeholder="Marcus" value={form.first_name} onChange={e => set('first_name', e.target.value)} required
                      onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                  </div>
                  <div>
                    <label style={labelStyle}>Last name</label>
                    <input style={inputStyle} type="text" placeholder="Thompson" value={form.last_name} onChange={e => set('last_name', e.target.value)} required
                      onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                  </div>
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Work email</label>
                  <input style={inputStyle} type="email" placeholder="marcus@cityauto.com" value={form.email} onChange={e => set('email', e.target.value)} required
                    onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Shop name</label>
                  <input style={inputStyle} type="text" placeholder="City Auto Center" value={form.shop_name} onChange={e => set('shop_name', e.target.value)} required
                    onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')} />
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Number of locations</label>
                  <select style={{ ...inputStyle, cursor: 'pointer' }} value={form.locations} onChange={e => set('locations', e.target.value)} required>
                    <option value="">Select...</option>
                    <option>1 location</option>
                    <option>2–5 locations</option>
                    <option>6–20 locations</option>
                    <option>20+ locations</option>
                  </select>
                </div>
                <div style={{ marginBottom: 18 }}>
                  <label style={labelStyle}>Anything you&apos;d like us to know? <span style={{ color: '#94a3b8', fontWeight: 400 }}>(optional)</span></label>
                  <textarea style={{ ...inputStyle, resize: 'vertical', minHeight: 90 }}
                    placeholder="e.g. We run 3 bays and want to speed up inspection write-ups..."
                    value={form.message} onChange={e => set('message', e.target.value)}
                    onFocus={e => (e.target.style.borderColor = '#2563eb')} onBlur={e => (e.target.style.borderColor = '#e2e8f0')}
                  />
                </div>

                {error && <p style={{ fontSize: 13, color: '#ef4444', marginBottom: 12 }}>{error}</p>}

                <button type="submit" disabled={loading} style={{
                  width: '100%', padding: 13, background: loading ? '#93c5fd' : '#2563eb',
                  color: '#fff', border: 'none', borderRadius: 10,
                  fontSize: 15, fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
                  boxShadow: '0 2px 10px rgba(37,99,235,0.3)',
                }}>
                  {loading ? 'Sending…' : 'Request Demo →'}
                </button>
                <p style={{ fontSize: 11.5, color: '#94a3b8', marginTop: 12, textAlign: 'center', lineHeight: 1.5 }}>No spam. We&apos;ll only reach out about your demo request.</p>
              </form>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
```

- [ ] **Step 2: Verify demo page renders and form submits**

Open `http://localhost:3000/demo`. Fill out the form and submit. With the backend running, the form should submit and show the confirmation state ("We'll be in touch!").

- [ ] **Step 3: Commit**

```bash
git add web/app/demo/page.tsx
git commit -m "feat(web): add /demo request page"
```

---

## Task 9: Google Cloud Console setup (environment config)

This task is manual — the implementor does it once.

- [ ] **Step 1: Create a Google OAuth 2.0 Client ID**

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a project (or use existing)
3. APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID
4. Application type: **Web application**
5. Authorized JavaScript origins: `http://localhost:3000` (dev) + your production domain
6. Authorized redirect URIs: not needed for the Identity Services flow
7. Copy the Client ID

- [ ] **Step 2: Set env vars**

Backend (Railway or local `.env`):
```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Frontend (`web/.env.local` for local, Vercel env vars for production):
```
NEXT_PUBLIC_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

- [ ] **Step 3: Test the full Google OAuth flow**

1. Start the backend: `cd backend && uvicorn src.api.main:app --reload`
2. Start the frontend: `cd web && npm run dev`
3. Open `http://localhost:3000/login`
4. Click "Continue with Google" — sign in with a Google account whose email matches a user in the DB
5. Verify it redirects to `/chat` with a valid token in localStorage

---

## Self-Review Against Spec

| Spec requirement | Task |
|---|---|
| `/` → marketing homepage | Task 1 + Task 6 |
| `/dashboard` → DashboardPage | Task 1 |
| Homepage: nav, hero, metrics, product (4 cards), why, testimonial, pricing, footer | Task 6 |
| $39/month Starter + Enterprise "Let's talk" | Task 6 |
| `/login` → Google OAuth + email/password | Task 7 |
| `POST /auth/google` backend endpoint | Task 4 |
| `GOOGLE_CLIENT_ID` env var | Task 2 + Task 9 |
| `/demo` full-page form | Task 8 |
| `POST /demo/request` backend endpoint | Task 5 |
| `demo_requests` DB table | Task 3 |
| `google_id` on users, `hashed_password` nullable | Task 3 |
| Alembic migration | Task 3 |
