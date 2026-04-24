import os
import pytest
import uuid
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.models.chat_message import ChatMessage
from src.db.base import Base

TEST_DB = os.environ["DATABASE_URL"]


@pytest.fixture
async def db_session():
    engine = create_async_engine(TEST_DB)
    shop_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        await s.execute(
            text(
                "INSERT INTO shops (id, name, labor_rate, pricing_flag) "
                "VALUES (:id, :name, 120, :flag)"
            ),
            {"id": str(shop_id), "name": f"Test Shop {shop_id}", "flag": "shop"},
        )
        await s.execute(
            text(
                "INSERT INTO users (id, shop_id, email, hashed_password, role) "
                "VALUES (:id, :shop_id, :email, :pw, :role)"
            ),
            {"id": str(user_id), "shop_id": str(shop_id), "email": f"test-{user_id}@example.com", "pw": "hashed", "role": "technician"},
        )
        await s.commit()

        s.info["user_id"] = user_id
        yield s

        await s.execute(text("DELETE FROM chat_messages WHERE user_id = :uid"), {"uid": str(user_id)})
        await s.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": str(user_id)})
        await s.execute(text("DELETE FROM shops WHERE id = :sid"), {"sid": str(shop_id)})
        await s.commit()

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_chat_message(db_session):
    user_id = db_session.info["user_id"]
    msg = ChatMessage(
        user_id=user_id,
        agent_id="assistant",
        role="user",
        content=[{"type": "text", "text": "Hello"}],
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)
    assert msg.id is not None
    assert msg.agent_id == "assistant"
    assert msg.tool_calls is None
