import logging
from typing import TypeVar

import sqlalchemy
from databases import Database
from pydantic import BaseModel
from sqlalchemy import create_engine

from .proxy import Session

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class Engine:
    def __init__(self, url: str, **kwargs):
        self.url = url
        self.db = Database(url, **kwargs)

        sync_url = (
            url.replace("+aiosqlite", "")
            .replace("+aiomysql", "+pymysql")  # MySQL 异步转同步
            .replace("+asyncpg", "")  # PostgreSQL 异步转同步
        )
        self._sync_engine = create_engine(sync_url)

    def init_db(self, metadata: sqlalchemy.MetaData):
        """
        根据定义的 Base.metadata 自动在数据库中创建所有缺失的表。
        """
        try:
            metadata.create_all(self._sync_engine)
            logger.info(">>> [SQLAlchemy-Lite] 数据库表结构初始化成功")
        except Exception as e:
            logger.exception(f">>> [SQLAlchemy-Lite] 数据库初始化失败: {e}")
            raise

    async def connect(self):
        await self.db.connect()

    async def disconnect(self):
        await self.db.disconnect()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def session(self):
        async with self.db.connection() as conn:
            yield Session(conn)

    # def select_for(self, model: Any, schema: Type[T]):
    #     """根据 Pydantic Schema 自动投影列"""
    #     cols = [
    #         getattr(model, f) for f in schema.model_fields.keys() if hasattr(model, f)
    #     ]
    #     return select(*(cols or [model]))
