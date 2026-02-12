import os
import tempfile

import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

from sqlalchemy_lite import Engine, fetch_page, select_for

# --- 环境准备 ---
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)


class UserSchema(BaseModel):
    id: int
    name: str


class TestPagination:
    """分页功能专项测试套件"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_db(self):
        """为每个测试方法初始化独立的内存/临时文件数据库"""
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp_path = tmp.name
        tmp.close()

        self.url = f"sqlite+aiosqlite:///{self.tmp_path}"
        self.engine = Engine(self.url)
        self.engine.init_db(Base.metadata)
        await self.engine.connect()

        # 共享 stmt
        self.stmt = select_for(User, UserSchema)

        yield

        await self.engine.disconnect()
        if os.path.exists(self.tmp_path):
            os.remove(self.tmp_path)

    async def _seed_data(self, count: int):
        """辅助方法：填充测试数据"""
        for i in range(count):
            await self.engine.db.execute(
                "INSERT INTO users (name) VALUES (:name)", {"name": f"user_{i}"}
            )

    @pytest.mark.asyncio
    async def test_empty_table_returns_valid_struct(self):
        """测试场景：空表状态下的返回结构"""
        async with self.engine.session() as sess:
            result = await fetch_page(sess, self.stmt, UserSchema, page=1, size=10)

            assert result.total == 0
            assert result.items == []
            assert result.total_pages == 0
            assert result.has_next is False

    @pytest.mark.asyncio
    async def test_normal_pagination_first_page(self):
        """测试场景：正常获取第一页数据"""
        await self._seed_data(25)
        async with self.engine.session() as sess:
            result = await fetch_page(sess, self.stmt, UserSchema, page=1, size=10)

            assert len(result.items) == 10
            assert result.total == 25
            assert result.total_pages == 3
            assert result.has_next is True
            assert result.has_prev is False

    @pytest.mark.asyncio
    async def test_negative_page_auto_correction(self):
        """测试场景：非法负数页码应自动纠正为第一页"""
        await self._seed_data(5)
        async with self.engine.session() as sess:
            # 传入 -5，逻辑应将其视为 1
            result = await fetch_page(sess, self.stmt, UserSchema, page=-5, size=10)
            assert result.page == 1
            assert len(result.items) == 5

    @pytest.mark.asyncio
    async def test_page_overflow_returns_empty_list(self):
        """测试场景：请求页码超出总页数时返回空列表"""
        await self._seed_data(15)  # 总共 2 页 (size=10)
        async with self.engine.session() as sess:
            result = await fetch_page(sess, self.stmt, UserSchema, page=3, size=10)

            assert result.total == 15
            assert result.items == []
            assert result.page == 3
            assert result.has_next is False

    @pytest.mark.asyncio
    async def test_last_page_contains_remaining_items(self):
        """测试场景：最后一页应包含正确的剩余项数"""
        await self._seed_data(25)
        async with self.engine.session() as sess:
            result = await fetch_page(sess, self.stmt, UserSchema, page=3, size=10)

            assert len(result.items) == 5
            assert result.has_next is False
            assert result.has_prev is True

    @pytest.mark.asyncio
    async def test_zero_size_protection(self):
        """测试场景：当每页大小设为 0 时的健壮性"""
        await self._seed_data(10)
        async with self.engine.session() as sess:
            # fetch_page 内部应将 size 纠正为 1
            result = await fetch_page(sess, self.stmt, UserSchema, page=1, size=0)
            assert result.size == 1
            assert result.total == 10
