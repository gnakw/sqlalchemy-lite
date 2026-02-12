import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from sqlalchemy_lite.engine import Engine
from sqlalchemy_lite.utils import fetch_page, select_for


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "test_users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    secret_token: Mapped[str] = mapped_column(String(50))  # 敏感字段


class UserSchema(BaseModel):
    username: str  # 仅查询此字段


@pytest_asyncio.fixture(scope="function")
async def db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    p = Path(db_path)
    service = Engine(f"sqlite+aiosqlite:///{db_path}")

    try:
        service.init_db(Base.metadata)
        await service.connect()
        yield service
    finally:
        try:
            await service.disconnect()
        except Exception:
            pass

        p.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_select_for_and_execute(db: Engine):
    async with db.session() as sess:
        async with sess.begin():
            # 插入数据
            from sqlalchemy import insert

            await sess.execute(
                insert(User).values(username="test", secret_token="secret")
            )

        # 测试自动投影查询
        stmt = select_for(User, UserSchema)
        result = await sess.execute(stmt)
        mappings = result.mappings()

        assert len(mappings) == 1
        assert "username" in mappings[0]
        assert "secret_token" not in mappings[0]  # 验证字段精简生效


@pytest.mark.asyncio
async def test_pagination(db: Engine):
    async with db.session() as sess:
        async with sess.begin():
            from sqlalchemy import insert

            # 批量插入 15 条
            for i in range(15):
                await sess.execute(
                    insert(User).values(username=f"user_{i}", secret_token="x")
                )

        stmt = select_for(User, UserSchema)
        page = await fetch_page(sess, stmt, UserSchema, page=2, size=5)

        assert page.total == 15
        assert len(page.items) == 5
        assert page.page == 2
