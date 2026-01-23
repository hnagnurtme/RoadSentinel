"""
Global exception handling middleware.
"""
import logging
from django.http import JsonResponse
from rest_framework.exceptions import APIException
from shared.responses.error import ErrorResponse

logger = logging.getLogger(__name__)


class ExceptionMiddleware:
    """Middleware to handle exceptions globally."""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        return response
    
    def process_exception(self, request, exception):
        """Process exceptions and return formatted error responses."""
        logger.error(f"Exception occurred: {str(exception)}", exc_info=True)
        
        if isinstance(exception, APIException):
            return ErrorResponse(
                message=str(exception.detail),
                status_code=exception.status_code
            )
        
        # Handle other exceptions
        return ErrorResponse(
            message="An unexpected error occurred",
            status_code=500
        )
