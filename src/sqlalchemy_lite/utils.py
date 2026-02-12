from typing import Any, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import func, select

from sqlalchemy_lite.types import PageResult

T = TypeVar("T", bound=BaseModel)


def get_select_columns(db_model: Any, schema: Type[T]):
    """
    根据 Pydantic Schema 提取 SQLAlchemy Model 的 Column 对象
    """
    selected_columns = [
        getattr(db_model, field_name)
        for field_name in schema.model_fields.keys()
        if hasattr(db_model, field_name)
    ]

    # 如果没有匹配到任何列，默认返回模型本身 (SELECT *)
    return selected_columns if selected_columns else [db_model]


def select_for(db_model: Any, schema: Type[T]):
    """
    根据 Pydantic 模型自动生成精简字段的SQLAlchemy select 语句
    """
    columns = get_select_columns(db_model, schema)
    return select(*columns)


async def fetch_page(
    session, stmt, schema: Type[T], page: int, size: int
) -> PageResult[T]:
    safe_page = max(1, page)
    safe_size = max(1, size)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = await session.scalar(count_stmt) or 0

    total_pages = (total + safe_size - 1) // safe_size if total > 0 else 1

    if safe_page > total_pages or total == 0:
        return PageResult(items=[], total=total, page=safe_page, size=safe_size)

    offset = (safe_page - 1) * safe_size
    paged_stmt = stmt.offset(offset).limit(safe_size)
    result = await session.execute(paged_stmt)

    items = [schema.model_validate(m) for m in result.mappings()]
    return PageResult(items=items, total=total, page=safe_page, size=safe_size)
