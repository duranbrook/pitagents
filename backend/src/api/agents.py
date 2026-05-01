import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.base import get_db
from src.api.deps import get_current_shop_id
from src.models.shop_agent import ShopAgent
from src.agents.tool_registry import TOOL_REGISTRY

router = APIRouter(prefix="/agents", tags=["agents"])

DEFAULT_AGENTS = [
    {
        "name": "Service Advisor",
        "role_tagline": "Front desk · Customer intake",
        "accent_color": "#d97706",
        "initials": "SA",
        "system_prompt": (
            "You are the Service Advisor at this auto shop, working at the front desk. "
            "Your domain: customers, vehicles, appointments, service reminders, invoices, and marketing. "
            "Use lookup_customer to find customer records. Use find_sessions_by_vehicle to surface "
            "reports the technician generated for a vehicle. "
            "The customer → vehicle → report chain is the core handoff: when the technician generates "
            "a report, you can pull it up here by customer name or vehicle."
        ),
        "tools": ["shop_data", "vin_lookup"],
        "sort_order": 0,
    },
    {
        "name": "Technician",
        "role_tagline": "Bay · Inspect & diagnose",
        "accent_color": "#3b82f6",
        "initials": "TK",
        "system_prompt": (
            "You are the Technician at this auto shop, working in the service bay. "
            "Your domain: vehicle inspection, AI diagnosis via DTC codes, job cards, and repair quotes. "
            "Use lookup_customer then get_customer_vehicles then find_sessions_by_vehicle to see prior "
            "service history for a vehicle. Build quotes using estimate_labor and create_quote. "
            "Every report you generate is automatically linked to the vehicle and visible to the Service Advisor."
        ),
        "tools": ["vin_lookup", "quote_builder", "parts_search", "shop_data"],
        "sort_order": 1,
    },
    {
        "name": "Parts Manager",
        "role_tagline": "Parts room · Inventory & vendors",
        "accent_color": "#06b6d4",
        "initials": "PM",
        "system_prompt": (
            "You are the Parts Manager at this auto shop, working in the parts room. "
            "Your domain: parts lookup by name or OEM code, inventory levels, and vendor relationships. "
            "Use semantic_parts_search to find parts. If a part is not in inventory, "
            "suggest creating a vendor purchase order."
        ),
        "tools": ["parts_search"],
        "sort_order": 2,
    },
    {
        "name": "Bookkeeper",
        "role_tagline": "Back office · Payments & accounting",
        "accent_color": "#22c55e",
        "initials": "BK",
        "system_prompt": (
            "You are the Bookkeeper at this auto shop, working in the back office. "
            "Your domain: payment reconciliation and accounting. "
            "You receive invoices created by the Service Advisor — you do not create invoices yourself. "
            "Answer questions about outstanding balances, monthly collections, and expenses."
        ),
        "tools": [],
        "sort_order": 3,
    },
    {
        "name": "Manager",
        "role_tagline": "Oversight · Reports & time tracking",
        "accent_color": "#a855f7",
        "initials": "MG",
        "system_prompt": (
            "You are the Shop Manager with oversight of all operations. "
            "Your domain: business-wide data — sessions, reports, and staff time tracking. "
            "Use list_sessions to see all recent shop activity. Use get_report to pull the findings "
            "for any session. Summarise trends and flag issues."
        ),
        "tools": ["shop_data"],
        "sort_order": 4,
    },
]


class AgentResponse(BaseModel):
    id: str
    name: str
    role_tagline: str
    accent_color: str
    initials: str
    system_prompt: str
    tools: list[str]
    sort_order: int


class AgentCreate(BaseModel):
    name: str
    role_tagline: str
    accent_color: str = "#d97706"
    initials: str
    system_prompt: str
    tools: list[str] = []
    sort_order: int = 99


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role_tagline: Optional[str] = None
    accent_color: Optional[str] = None
    initials: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[list[str]] = None
    sort_order: Optional[int] = None


def _to_response(a: ShopAgent) -> AgentResponse:
    return AgentResponse(
        id=str(a.id),
        name=a.name,
        role_tagline=a.role_tagline,
        accent_color=a.accent_color,
        initials=a.initials,
        system_prompt=a.system_prompt,
        tools=a.tools or [],
        sort_order=a.sort_order,
    )


async def _ensure_seeded(shop_id: uuid.UUID, db: AsyncSession) -> None:
    """Seed default agents if this shop has none."""
    result = await db.execute(
        select(ShopAgent).where(ShopAgent.shop_id == shop_id).limit(1)
    )
    if result.scalar_one_or_none() is not None:
        return
    for defn in DEFAULT_AGENTS:
        db.add(ShopAgent(shop_id=shop_id, **defn))
    await db.commit()


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    sid = uuid.UUID(shop_id)
    await _ensure_seeded(sid, db)
    result = await db.execute(
        select(ShopAgent)
        .where(ShopAgent.shop_id == sid)
        .order_by(ShopAgent.sort_order)
    )
    return [_to_response(a) for a in result.scalars().all()]


@router.get("/tools", response_model=list[dict])
async def list_tools(_: str = Depends(get_current_shop_id)):
    """Return the tool registry for use in the builder UI."""
    return [
        {"id": tid, "label": meta["label"], "description": meta["description"]}
        for tid, meta in TOOL_REGISTRY.items()
    ]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    body: AgentCreate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    agent = ShopAgent(shop_id=uuid.UUID(shop_id), **body.model_dump())
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return _to_response(agent)


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShopAgent).where(
            ShopAgent.id == uuid.UUID(agent_id),
            ShopAgent.shop_id == uuid.UUID(shop_id),
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(agent, field, val)
    await db.commit()
    await db.refresh(agent)
    from src.api.chat import _graph_cache
    _graph_cache.pop(agent_id, None)
    return _to_response(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: str,
    shop_id: str = Depends(get_current_shop_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ShopAgent).where(
            ShopAgent.id == uuid.UUID(agent_id),
            ShopAgent.shop_id == uuid.UUID(shop_id),
        )
    )
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    await db.delete(agent)
    await db.commit()
    from src.api.chat import _graph_cache
    _graph_cache.pop(agent_id, None)
