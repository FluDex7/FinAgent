class AppError(Exception):
    """Base for domain errors that should surface to the API as a 4xx response."""

    status_code: int = 422

    def __init__(self, message: str, *, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.hint = hint


class StatementParseError(AppError):
    pass


class PathTraversalError(AppError):
    pass


class StatementNotFoundError(AppError):
    status_code = 404


class StatementNameConflictError(AppError):
    status_code = 409


class SqlValidationError(AppError):
    pass


class MerchantNotFoundError(AppError):
    status_code = 404


class CategoryNotFoundError(AppError):
    status_code = 404
