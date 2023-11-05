"""Abstract web client class."""
from __future__ import annotations

import abc
from http import HTTPStatus

RETRYABLE_HTTP_STATUS_CODES: set[int] = {
    # Some servers return "400 Bad Request" initially but upon retry start working again, no idea why
    int(HTTPStatus.BAD_REQUEST),
    # If we timed out requesting stuff, we can just try again
    int(HTTPStatus.REQUEST_TIMEOUT),
    # If we got rate limited, it makes sense to wait a bit
    int(HTTPStatus.TOO_MANY_REQUESTS),
    # Server might be just fine on a subsequent attempt
    int(HTTPStatus.INTERNAL_SERVER_ERROR),
    # Upstream might reappear on a retry
    int(HTTPStatus.BAD_GATEWAY),
    # Service might become available again on a retry
    int(HTTPStatus.SERVICE_UNAVAILABLE),
    # Upstream might reappear on a retry
    int(HTTPStatus.GATEWAY_TIMEOUT),
    # (unofficial) 509 Bandwidth Limit Exceeded (Apache Web Server/cPanel)
    509,
    # (unofficial) 598 Network read timeout error
    598,
    # (unofficial, nginx) 499 Client Closed Request
    499,
    # (unofficial, Cloudflare) 520 Unknown Error
    520,
    # (unofficial, Cloudflare) 521 Web Server Is Down
    521,
    # (unofficial, Cloudflare) 522 Connection Timed Out
    522,
    # (unofficial, Cloudflare) 523 Origin Is Unreachable
    523,
    # (unofficial, Cloudflare) 524 A Timeout Occurred
    524,
    # (unofficial, Cloudflare) 525 SSL Handshake Failed
    525,
    # (unofficial, Cloudflare) 526 Invalid SSL Certificate
    526,
    # (unofficial, Cloudflare) 527 Railgun Error
    527,
    # (unofficial, Cloudflare) 530 Origin DNS Error
    530,
}
"""HTTP status codes on which a request should be retried."""


class AbstractWebClientResponse(metaclass=abc.ABCMeta):
    """Abstract response."""


class AbstractWebClientSuccessResponse(
    AbstractWebClientResponse,
    metaclass=abc.ABCMeta,
):
    """Successful response."""

    @abc.abstractmethod
    def status_code(self: AbstractWebClientSuccessResponse) -> int:
        """Return HTTP status code of the response.

        :return: HTTP status code of the response, e.g. 200.
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def status_message(self: AbstractWebClientSuccessResponse) -> str:
        """Return HTTP status message of the response.

        :return: HTTP status message of the response, e.g. "OK".
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def header(
        self: AbstractWebClientSuccessResponse,
        case_insensitive_name: str,
    ) -> str | None:
        """Return value of a header of the response."""
        msg = "Abstract method."
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def raw_data(self: AbstractWebClientSuccessResponse) -> bytes:
        """Return encoded raw data of the response.

        :return: Encoded raw data of the response.
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)


class WebClientErrorResponse(AbstractWebClientResponse, metaclass=abc.ABCMeta):
    """Error response."""

    __slots__: list[str] = [
        "_message",
        "_retryable",
    ]

    def __init__(
        self: WebClientErrorResponse,
        message: str,
        *,
        retryable: bool,
    ) -> None:
        """Initialize the error response.

        Args:
            self: Instance.
            message: Message describing what went wrong.
            retryable: True if request should be retried.
        """
        super().__init__()
        self._message: str = message
        self._retryable: bool = retryable

    def message(self: WebClientErrorResponse) -> str:
        """Return message describing what went wrong.

        Args:
            self: Instance.

        Returns:
            Message describing what went wrong.
        """
        return self._message

    def retryable(self: WebClientErrorResponse) -> bool:
        """Return True if request should be retried.

        Args:
            self: Instance.

        Returns:
            True if request should be retried.
        """
        return self._retryable


class AbstractWebClient(metaclass=abc.ABCMeta):
    """Abstract web client to be used by the sitemap fetcher."""

    @abc.abstractmethod
    def set_max_response_data_length(
        self: AbstractWebClient,
        max_response_data_length: int,
    ) -> None:
        """Set maximum length of response data.

        Args:
            self: Instance.
            max_response_data_length: Maximum length of response data.

        Raises:
            NotImplementedError: Always.
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def get(self: AbstractWebClient, url: str) -> AbstractWebClientResponse:
        """Fetch URL.

        Args:
            self: Instance.
            url: URL to fetch.

        Raises:
            NotImplementedError: Always.

        Returns:
            Response object.
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)
