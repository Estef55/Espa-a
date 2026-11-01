"""Errores de dominio. Cada uno lleva el código HTTP con el que la capa web lo expone."""
from __future__ import annotations


class I3Error(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str = "", **extra):
        super().__init__(message or self.code)
        self.message = message or self.code
        self.extra = extra

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, **self.extra}


class ValidationError(I3Error):
    status_code, code = 422, "validation_error"


class Unauthorized(I3Error):
    status_code, code = 401, "unauthorized"


class Forbidden(I3Error):
    status_code, code = 403, "forbidden"


class NotFound(I3Error):
    status_code, code = 404, "not_found"


class Conflict(I3Error):
    status_code, code = 409, "version_conflict"


class AuthNotConfigured(I3Error):
    status_code, code = 503, "auth_not_configured"


class IntegrationNotConfigured(I3Error):
    status_code, code = 503, "integration_not_configured"


class DataSourceNotConfigured(I3Error):
    status_code, code = 503, "data_source_not_configured"


class ProviderNotConfigured(I3Error):
    status_code, code = 503, "ai_provider_not_configured"


class ProviderTimeout(I3Error):
    status_code, code = 504, "ai_provider_timeout"


class ProviderError(I3Error):
    status_code, code = 502, "ai_provider_error"


class EmptyProviderResponse(ProviderError):
    code = "ai_empty_response"
