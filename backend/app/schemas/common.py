"""Shared schema building blocks used across every module."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard list-endpoint envelope - see documentation/project-scope.md, section 9.

    Every list endpoint in the API returns this shape:

        {"items": [...], "page": 1, "page_size": 20, "total_items": 0, "total_pages": 0}

    rather than a bare array, so the frontend always has paging metadata
    available without a separate count request.
    """

    items: list[T]
    page: int
    page_size: int
    total_items: int
    total_pages: int
