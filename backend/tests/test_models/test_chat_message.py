import pytest
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.models.chat_message import ChatMessage
from src.db.base import Base

TEST_DB = "postgresql+asyncpg://user:password@db:5432/autoshop"


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, class_=AsyncSession)
    async with maker() as s:
        # Insert a shop and user to satisfy FK constraints
        shop_id = uuid.uuid4()
        user_id = uuid.uuid4()
        await s.execute(
            text(
                "INSERT INTO shops (id, name, labor_rate, pricing_flag) "
                "VALUES (:id, 'Test Shop', 120, 'shop') ON CONFLICT DO NOTHING"
            ),
            {"id": str(shop_id)},
        )
        await s.execute(
            text(
                "INSERT INTO users (id, shop_id, email, hashed_password, role) "
                "VALUES (:id, :shop_id, 'test@example.com', 'hashed', 'technician') ON CONFLICT DO NOTHING"
            ),
            {"id": str(user_id), "shop_id": str(shop_id)},
        )
        await s.commit()
        s.info["user_id"] = user_id
        yield s
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM chat_messages"))
        await conn.execute(text("DELETE FROM users WHERE email = 'test@example.com'"))
        await conn.execute(text("DELETE FROM shops WHERE name = 'Test Shop'"))


@pytest.mark.asyncio
async def test_create_chat_message(session):
    user_id = session.info["user_id"]
    msg = ChatMessage(
        user_id=user_id,
        agent_id="assistant",
        role="user",
        content=[{"type": "text", "text": "Hello"}],
    )
    session.add(msg)
    await session.commit()
    await session.refresh(msg)
    assert msg.id is not None
    assert msg.agent_id == "assistant"
    assert msg.tool_calls is None
