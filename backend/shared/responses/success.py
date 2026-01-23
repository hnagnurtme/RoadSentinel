"""
Standard success response.
"""
from rest_framework import status
from shared.responses.base import BaseResponse


class SuccessResponse(BaseResponse):
    """Response class for successful operations."""
    
    def __init__(self, data=None, message='Success', status_code=status.HTTP_200_OK, **kwargs):
        """
        Initialize success response.
        
        Args:
            data: Response data
            message: Success message
            status_code: HTTP status code (default 200)
        """
        super().__init__(
            data=data,
            message=message,
            success=True,
            status_code=status_code,
            **kwargs
        )
