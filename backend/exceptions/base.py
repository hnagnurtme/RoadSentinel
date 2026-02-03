from typing import Any


class AppException(Exception) :
    def __init__(
            self,
            message : str ,
            *,
            status_code : int = 400,
            error_code : str | None  = None,
            detail : Any | None = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(message)