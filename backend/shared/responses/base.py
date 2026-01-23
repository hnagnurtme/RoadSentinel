"""
Base API response structure.
"""
from rest_framework.response import Response


class BaseResponse(Response):
    """Base class for all API responses."""
    
    def __init__(self, data=None, message='', success=True, status_code=200, **kwargs):
        """
        Initialize base response.
        
        Args:
            data: Response data
            message: Response message
            success: Success flag
            status_code: HTTP status code
        """
        response_data = {
            'success': success,
            'message': message,
            'data': data
        }
        
        super().__init__(data=response_data, status=status_code, **kwargs)
