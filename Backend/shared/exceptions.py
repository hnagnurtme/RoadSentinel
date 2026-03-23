class AppException(Exception):
	status_code = 400
	code = "APP_ERROR"

	def __init__(self, message: str):
		super().__init__(message)
		self.message = message


class NotFoundException(AppException):
	status_code = 404
	code = "NOT_FOUND"


class ConflictException(AppException):
	status_code = 409
	code = "CONFLICT"


class ValidationException(AppException):
	status_code = 422
	code = "VALIDATION_ERROR"

