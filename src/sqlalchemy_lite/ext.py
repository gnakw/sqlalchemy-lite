from functools import wraps
from typing import Type

from pydantic import BaseModel

from sqlalchemy_lite.utils import select_for


def auto_query(db_model, schema: Type[BaseModel], single: bool = False):
    """业务级装饰器, 自动查询

    Args:
        db_model (_type_): SQLAlchemy 模型
        schema (Type[BaseModel]): Pydantic 模型 (用于 select_for)
        single (bool, optional): 是否只返回单条数据 (result.first vs result.all)

    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # 1. 自动根据 Schema 构建基础语句
            base_stmt = select_for(db_model, schema)

            # 2. 执行原函数获取过滤条件 (如 .where())
            final_stmt = await func(self, base_stmt, *args, **kwargs)

            # 3. 统一处理 Session 执行逻辑
            async with self.db.session() as sess:
                result = await sess.execute(final_stmt)

                if single:
                    row = result.first()
                    return schema.model_validate(dict(row)) if row else None

                return [schema.model_validate(m) for m in result.mappings()]

        return wrapper

    return decorator
