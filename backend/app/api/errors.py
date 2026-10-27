"""Public-safe HTTP error mapping for upstream services."""

from fastapi import HTTPException

from ..services.qloo_service import QlooServiceError


def qloo_http_error(error: QlooServiceError) -> HTTPException:
    if error.code in {"QLOO_AUTH_FAILED", "QLOO_INVALID_RESPONSE"}:
        status_code = 502
    elif error.code == "QLOO_REQUEST_REJECTED":
        status_code = 422
    else:
        status_code = 503
    return HTTPException(
        status_code=status_code,
        detail={
            "error_code": error.code,
            "message": str(error),
            "retryable": error.retryable,
        },
    )
