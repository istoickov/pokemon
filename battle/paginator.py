from dataclasses import dataclass
from typing import Any, Dict, Generic, List, TypeVar

from django.db.models import QuerySet

T = TypeVar("T")


@dataclass
class PaginationInfo:
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_count": self.total_count,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


class Paginator(Generic[T]):
    def __init__(self, queryset: QuerySet, page: int = 1, page_size: int = 20):
        self.queryset = queryset
        self.page = max(1, page)  # Ensure page is at least 1
        self.page_size = max(1, page_size)  # Ensure page_size is at least 1
        self.total_count = queryset.count()
        self.total_pages = (self.total_count + self.page_size - 1) // self.page_size

        # Adjust page if it's beyond total pages
        if self.page > self.total_pages and self.total_pages > 0:
            self.page = self.total_pages

    def get_page_items(self) -> List[T]:
        """Get the items for the current page."""
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return list(self.queryset[start:end])

    def get_pagination_info(self) -> PaginationInfo:
        """Get pagination metadata."""
        return PaginationInfo(
            page=self.page,
            page_size=self.page_size,
            total_count=self.total_count,
            total_pages=self.total_pages,
            has_next=self.page < self.total_pages,
            has_previous=self.page > 1,
        )

    def paginate(self) -> Dict[str, Any]:
        """Get paginated results with metadata."""
        return {
            "items": self.get_page_items(),
            "pagination": self.get_pagination_info().to_dict(),
        }
