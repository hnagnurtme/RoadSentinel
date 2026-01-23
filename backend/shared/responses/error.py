"""
Error response structure.
"""
from rest_framework import status
from shared.responses.base import BaseResponse


class ErrorResponse(BaseResponse):
    """Response class for error cases."""
    
    def __init__(self, message='An error occurred', errors=None, status_code=status.HTTP_400_BAD_REQUEST, **kwargs):
        """
        Initialize error response.
        
        Args:
            message: Error message
            errors: Detailed error information (optional)
            status_code: HTTP status code
        """
        error_data = None
        if errors:
            error_data = {'errors': errors}
        
        super().__init__(
            data=error_data,
            message=message,
            success=False,
            status_code=status_code,
            **kwargs
        )
