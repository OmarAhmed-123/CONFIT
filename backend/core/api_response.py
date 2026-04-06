from typing import Any, Optional


def ok(data: Any = None) -> dict:
    return {
        "success": True,
        "data": data,
        "error": None,
    }


def fail(error: str, data: Optional[Any] = None) -> dict:
    return {
        "success": False,
        "data": data,
        "error": error,
    }

