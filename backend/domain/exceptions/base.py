class DomainError(Exception):
    code = "DOMAIN_ERROR"
    status_code = 400

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    code, status_code = "VALIDATION_ERROR", 400


class AuthenticationError(DomainError):
    code, status_code = "AUTHENTICATION_ERROR", 401


class AuthorizationError(DomainError):
    code, status_code = "AUTHORIZATION_ERROR", 403


class NotFoundError(DomainError):
    code, status_code = "NOT_FOUND", 404


class ConflictError(DomainError):
    code, status_code = "CONFLICT", 409


class StorageError(DomainError):
    code, status_code = "STORAGE_ERROR", 503


class ExternalServiceError(DomainError):
    code, status_code = "EXTERNAL_SERVICE_ERROR", 502


class IngestionError(DomainError):
    code, status_code = "INGESTION_ERROR", 422
