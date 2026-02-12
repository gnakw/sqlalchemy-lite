import math
from typing import Generic, List, TypeVar

from pydantic import BaseModel, ConfigDict, computed_field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int

    @computed_field
    @property
    def total_pages(self) -> int:
        if self.size <= 0:
            return 0
        return math.ceil(self.total / self.size)

    @computed_field
    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @computed_field
    @property
    def has_prev(self) -> bool:
        return self.page > 1

    model_config = ConfigDict(from_attributes=True)
