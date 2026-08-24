import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from apps.common.exceptions import (
    NotFoundError,
    PermissionDeniedError,
    PricePilotError,
    ValidationError,
)

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
}


def envelope(data=None, error=None):
    """Standard response shape used across every PricePilot endpoint."""
    return {"data": data, "error": error}


def custom_exception_handler(exc, context):
    """Wraps DRF's default handler so:

    1. Domain exceptions (apps.common.exceptions.*) map to sane HTTP codes.
    2. Every error response has the same {"data": None, "error": {...}} shape.
    3. Nothing fails silently — every unhandled exception is logged.
    """
    if isinstance(exc, PricePilotError):
        code = _STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
        logger.warning("Domain error: %s", exc.message, exc_info=exc)
        return Response(
            envelope(error={"message": exc.message, "type": type(exc).__name__}),
            status=code,
        )

    response = drf_exception_handler(exc, context)

    if response is not None:
        response.data = envelope(error={"message": str(exc), "detail": response.data})
        return response

    # Unhandled exception — log with full traceback, never fail silently.
    logger.exception("Unhandled exception in view", exc_info=exc)
    return Response(
        envelope(error={"message": "Internal server error."}),
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
