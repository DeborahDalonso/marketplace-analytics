from typing import Any


def ok(data: Any = None, message: str | None = None) -> dict[str, Any]:
    return {'success': True, 'message': message, 'data': data}


def fail(message: str, errors: list[dict[str, str]] | None = None) -> dict[str, Any]:
    return {'success': False, 'message': message, 'errors': errors or []}
