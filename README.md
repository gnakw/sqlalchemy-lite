# SQLAlchemy-Lite 🚀

**SQLAlchemy-Lite** 是一个专为受限环境（如老旧 ARM 设备、嵌入式系统）设计的轻量级异步数据库适配层。

> **核心定位**：A future-proof, greenlet-free adapter for SQLAlchemy 2.0 and databases.

它通过缝合 **SQLAlchemy 2.0 的表达式能力**、**databases 的异步驱动桥接** 以及 **Pydantic 的数据校验**，在彻底摆脱 `greenlet` 依赖的同时，提供了一套现代化的开发体验。

---

## 🌟 核心特性

- **去 Greenlet 化**: 彻底避开原生 `AsyncSession` 对 `greenlet` 的硬依赖，解决在特定硬件上无法编译或运行的问题。
- **Schema 驱动查询**: 配合 `select_for` 工具，自动根据 Pydantic 模型生成精简的 SQL 投影，仅查询所需字段，极大压榨老旧设备的 IO 性能。
- **2.0 风格语法**: 100% 兼容 SQLAlchemy 2.0 的 `select`, `insert`, `update`, `delete` 表达式构造。
- **多数据库适配**: 原生支持 **SQLite**, **MySQL**, 及 **PostgreSQL**，支持连接池管理。
- **类型安全**: 内置 `py.typed`，对 Mypy 和 IDE 自动补全友好。
- **原生分页支持**：内置 `fetch_page` 异步工具，支持物理分页与总数自动统计，并提供包含 `total_pages`、`has_next` 等智能属性的返回容器。

---

## 📦 安装

使用 [uv](https://github.com/astral-sh/uv) 或 pip 进行安装：

```bash
# 基础安装 (含核心逻辑)
uv add sqlalchemy-lite

# 根据需求安装数据库驱动扩展
uv add "sqlalchemy-lite[sqlite]"   # 默认 SQLite
uv add "sqlalchemy-lite[mysql]"    # MySQL 支持
uv add "sqlalchemy-lite[postgres]" # PostgreSQL 支持

```

---

## 🛠️ 快速上手

### 1. 定义数据结构

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from pydantic import BaseModel

class Base(DeclarativeBase): pass

# 数据库模型
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column()
    bio: Mapped[str] = mapped_column() # 大字段，非必要不查询

# 业务视图模型
class UserSimple(BaseModel):
    username: str
    email: str

```

### 2. 核心查询示例

```python
from sqlalchemy_lite import Engine, select_for

async def main():
    db = Engine("sqlite+aiosqlite:///app.db")
    db.init_db(Base.metadata)

    await db.connect()

    async with db.session() as sess:
        # 自动生成精简 SQL: SELECT username, email FROM users
        stmt = select_for(User, UserSimple)
        result = await sess.execute(stmt)
        
        # 映射为 Pydantic 对象列表
        users = [UserSimple.model_validate(m) for m in result.mappings()]
    
    await db.disconnect()

```

---

## 📖 标准业务服务模板 (Best Practice)

为了确保代码的健壮性与可移植性，推荐采用以下模式：

```python
from sqlalchemy_lite import auto_query, PageResult, select_for, fetch_page

class UserService:
    def __init__(self, db: Engine):
        self.db = db

    @auto_query(User, UserSimple, single=True)
    async def get_by_name(self, stmt, name: str):
        """使用装饰器：自动处理 session 开启、SQL 投影与模型验证"""
        return stmt.where(User.username == name)

    async def list_paged(self, page: int, size: int) -> PageResult[UserSimple]:
        """标准分页：计算总数 + 物理分页 + 结果包装"""
        async with self.db.session() as sess:
            base_stmt = select_for(User, UserSimple)
            return await fetch_page(sess, base_stmt, UserSimple, page, size)

```

---

## 🛡️ 模板关键原则 (The Principles)

| 维度 | 推荐做法 (未来证明) | 禁忌做法 |
| --- | --- | --- |
| **查询列** | 使用 `select_for` 或明确指定列 | 严禁 `select(User)` (全实体查询) |
| **单条转换** | `Schema.model_validate(dict(row))` | 严禁依赖 ORM 的延迟加载属性 |
| **结果访问** | 使用 `result.mappings()` 或 `result.scalar()` | 严禁依赖 `result.scalars().all()` 获取整个对象 |
| **事务** | 始终使用 `async with session.begin():` | 手动显式调用 `commit()` |

---

## 🔗 高级配置与连接池

对于 **MySQL** 或 **PostgreSQL**，建议配置连接池以提升性能：

```python
db = Engine(
    url="mysql+aiomysql://root:pass@localhost/db",
    min_size=5,
    max_size=20,
    pool_recycle=3600
)

```

---

## 💎 未来证明 (Future-Proofing)

**SQLAlchemy-Lite** 的设计理念是“不产生负担”。当你不再受限于硬件环境，想要迁移回官方的 SQLAlchemy `AsyncSession` 时：

1. **零逻辑修改**: 由于 `select_for` 生成的是标准 SQLAlchemy 语句，你的业务函数体无需任何修改。
2. **零迁移成本**: 我们的 `Session` 和 `Result` 接口高度模拟了官方 API。你只需将 `Engine` 替换为 `create_async_engine`，并调整 `Session` 获取方式即可。

---

## ⚖️ 开源协议

本项目采用 **MIT** 协议。

---

## Acknowledgment

This project was developed with the assistance of AI (Gemini). While the core architecture and logic were human-steered and rigorously reviewed to ensure security and compliance with SQLAlchemy 2.0 standards, this collaboration allowed for a more rapid exploration of lite-weight patterns for restricted environments.

