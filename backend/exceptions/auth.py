from exceptions.base import AppException


class UnauthorizedException(AppException):
    def __init__( self,message: str = "Unauthorized"):
        super().__init__(
            message= message,
            status_code= 401,
            error_code="UNAUTHORIZED"
        )
class ForbiddenException(AppException):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
        )