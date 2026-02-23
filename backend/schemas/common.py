from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: T | None = None

    model_config = ConfigDict(from_attributes=True)


class ErrorResponse(BaseModel):

    success: bool = False
    message: str
    error_code: str | None = None
    details: dict[str, Any] | None = None


class PaginationMeta(BaseModel):
    page: int
    per_page: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "Success"
    data: list[T]
    meta: PaginationMeta

    model_config = ConfigDict(from_attributes=True)


def create_pagination_meta(
    page: int,
    per_page: int,
    total_items: int,
) -> PaginationMeta:
    total_pages = (total_items + per_page - 1) // per_page if per_page > 0 else 0
    return PaginationMeta(
        page=page,
        per_page=per_page,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
