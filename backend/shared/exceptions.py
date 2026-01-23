"""
Shared custom exceptions.
"""
from rest_framework.exceptions import APIException
from rest_framework import status


class ValidationException(APIException):
    """Exception for validation errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Validation error occurred.'
    default_code = 'validation_error'


class NotFoundException(APIException):
    """Exception for resource not found."""
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Resource not found.'
    default_code = 'not_found'


class PermissionDeniedException(APIException):
    """Exception for permission denied."""
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'Permission denied.'
    default_code = 'permission_denied'


class UnauthorizedException(APIException):
    """Exception for unauthorized access."""
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = 'Unauthorized access.'
    default_code = 'unauthorized'


class ConflictException(APIException):
    """Exception for resource conflicts."""
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Resource conflict.'
    default_code = 'conflict'
