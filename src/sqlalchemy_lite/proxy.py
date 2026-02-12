from typing import Any, Dict, List, Optional, Union

from databases.interfaces import Record
from sqlalchemy.exc import MultipleResultsFound, NoResultFound


class ScalarResult:
    """处理 .scalars() 的降维结果集"""

    def __init__(self, rows: List[Record]):
        self._data = [row[0] for row in rows] if rows else []

    def all(self) -> List[Any]:
        return self._data

    def first(self) -> Optional[Any]:
        return self._data[0] if self._data else None

    def __iter__(self):
        return iter(self._data)


class Result:
    """模拟 SQLAlchemy 2.0 Result 接口"""

    def __init__(self, rows: Union[List[Record], Any]):
        self._rows = (
            rows if isinstance(rows, list) else ([rows] if rows is not None else [])
        )

    def all(self) -> List[Record]:
        return self._rows

    def first(self) -> Optional[Record]:
        return self._rows[0] if self._rows else None

    def one_or_none(self):
        """取第一行，如果有第二行则报错"""
        if len(self._rows) > 1:
            raise MultipleResultsFound(
                f"Expected at most one result, got {len(self._rows)}"
            )
        return self._rows[0] if self._rows else None

    def one(self):
        """必须有一行，且只能有一行"""
        if not self._rows:
            raise NoResultFound("No result found")
        if len(self._rows) > 1:
            raise MultipleResultsFound(
                f"Expected exactly one result, got {len(self._rows)}"
            )
        return self._rows[0]

    def scalar(self) -> Any:
        return self._rows[0][0] if self._rows and len(self._rows[0]) > 0 else None

    def scalar_one_or_none(self):
        """安全返回单值"""
        row = self.one_or_none()
        return row[0] if row else None

    def scalars(self) -> ScalarResult:
        return ScalarResult(self._rows)

    def mappings(self) -> List[Dict[str, Any]]:
        return [dict(row) for row in self._rows]

    def __iter__(self):
        return iter(self._rows)


class Session:
    """映射 SQLAlchemy Session 到 databases.Connection"""

    def __init__(self, conn):
        self._conn = conn

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def begin(self):
        async with self._conn.transaction():
            yield self

    async def execute(self, statement: Any) -> Result:
        raw_sql = str(statement).strip().upper()
        # 简单判别 SELECT 逻辑，亦可扩展更严谨的判断
        if raw_sql.startswith("SELECT") or "RETURNING" in raw_sql:
            rows = await self._conn.fetch_all(statement)
            return Result(rows)
        res = await self._conn.execute(statement)
        return Result(res)

    async def scalar(self, statement):
        res = await self.execute(statement)
        return res.scalar()
