from typing import Any


def success_response(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(message: str, code: str) -> dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "error": {
            "code": code,
        },
    }
