from http import HTTPStatus

from axiomai.application.exceptions.common import AppError
from axiomai.constants import SUPERBANKING_ERROR_BODY_PREVIEW_LENGTH


class SuperbankingRequestError(AppError):
    """HTTP-ошибка (4xx/5xx), невалидный ответ или сетевой сбой при обращении к Superbanking."""

    def __init__(self, log_context: str, status: int | None = None, body: str | None = None) -> None:
        self.log_context = log_context
        self.status = status
        self.body = body
        body_preview = body[:SUPERBANKING_ERROR_BODY_PREVIEW_LENGTH] if body else None
        super().__init__(f"Superbanking {log_context} failed: status={status}, body={body_preview}")

    @property
    def is_retryable(self) -> bool:
        """Сетевые ошибки, 5xx и 429 имеет смысл повторить; остальные 4xx — нет."""
        return (
            self.status is None
            or self.status >= HTTPStatus.INTERNAL_SERVER_ERROR
            or self.status == HTTPStatus.TOO_MANY_REQUESTS
        )


class CreatePaymentError(AppError):
    """Exception raised when Superbanking payment creation fails."""


class SignPaymentError(AppError):
    """Exception raised when Superbanking payment signing fails."""


class SkipSuperbankingError(AppError):
    """When is_superbanking_connect is False, this exception will raise"""

    def __init__(self, cabinet_id: int, *, is_superbanking_connect: bool) -> None:
        self.cabinet_id = cabinet_id
        self.is_superbanking_connect = is_superbanking_connect
