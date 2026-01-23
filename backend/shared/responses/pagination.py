"""
Paginated response format.
"""
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from shared.responses.base import BaseResponse


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination class."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PaginatedResponse(BaseResponse):
    """Response class for paginated data."""
    
    def __init__(self, data, count, page, page_size, message='Success', **kwargs):
        """
        Initialize paginated response.
        
        Args:
            data: List of items
            count: Total number of items
            page: Current page number
            page_size: Number of items per page
            message: Response message
        """
        paginated_data = {
            'items': data,
            'pagination': {
                'total': count,
                'page': page,
                'page_size': page_size,
                'total_pages': (count + page_size - 1) // page_size if page_size > 0 else 0
            }
        }
        
        super().__init__(
            data=paginated_data,
            message=message,
            success=True,
            status_code=status.HTTP_200_OK,
            **kwargs
        )
