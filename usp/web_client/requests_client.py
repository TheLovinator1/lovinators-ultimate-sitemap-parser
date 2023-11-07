"""requests-based implementation of web client class."""
from __future__ import annotations

from http import HTTPStatus

import requests

from .abstract_client import (
    RETRYABLE_HTTP_STATUS_CODES,
    AbstractWebClient,
    AbstractWebClientResponse,
    AbstractWebClientSuccessResponse,
    WebClientErrorResponse,
)


class RequestsWebClientSuccessResponse(AbstractWebClientSuccessResponse):
    """requests-based successful response."""

    __slots__: list[str] = [
        "__requests_response",
        "__max_response_data_length",
    ]

    def __init__(
        self: RequestsWebClientSuccessResponse,
        requests_response: requests.Response,
        max_response_data_length: int | None = None,
    ) -> None:
        """Initialize the successful response.

        Args:
            self: Instance.
            requests_response: requests response.
            max_response_data_length: Maximum length of response data.
        """
        self.__requests_response: requests.Response = requests_response
        self.__max_response_data_length: int | None = max_response_data_length

    def status_code(self: RequestsWebClientSuccessResponse) -> int:
        """Return HTTP status code.

        Returns:
            HTTP status code.
        """
        return int(self.__requests_response.status_code)

    def status_message(self: RequestsWebClientSuccessResponse) -> str:
        """Return HTTP status message.

        Args:
            self: Instance.

        Returns:
            HTTP status message.
        """
        message = self.__requests_response.reason
        if not message:
            message: str = HTTPStatus(self.status_code()).phrase
        return message

    def header(
        self: RequestsWebClientSuccessResponse,
        case_insensitive_name: str,
    ) -> str | None:
        """Return value of a header.

        Args:
            case_insensitive_name: Case-insensitive header name.

        Returns:
            Value of a header.
        """
        return self.__requests_response.headers.get(case_insensitive_name.lower(), None)

    def raw_data(self: RequestsWebClientSuccessResponse) -> bytes:
        """Return encoded raw data.

        Args:
            self: Instance.

        Returns:
            Encoded raw data.
        """
        data: bytes
        if self.__max_response_data_length:
            data = self.__requests_response.content[: self.__max_response_data_length]
        else:
            data = self.__requests_response.content

        return data


class RequestsWebClientErrorResponse(WebClientErrorResponse):
    """requests-based error response."""


class RequestsWebClient(AbstractWebClient):
    """requests-based web client to be used by the sitemap fetcher."""

    __USER_AGENT = "lovinators_ultimate_sitemap_parser/0.1.0"

    # HTTP request timeout.
    # Some web servers might be generating huge sitemaps on the fly, so this is why it's rather big.
    __HTTP_REQUEST_TIMEOUT = 60

    __slots__: list[str] = [
        "__max_response_data_length",
        "__timeout",
        "__proxies",
    ]

    def __init__(self: RequestsWebClient) -> None:
        """Initialize the web client.

        Args:
            self: Instance.
        """
        self.__max_response_data_length: int | None = None
        self.__timeout: int = self.__HTTP_REQUEST_TIMEOUT
        self.__proxies: dict[str, str] = {}

    def set_timeout(self: RequestsWebClient, timeout: int) -> None:
        """Set HTTP request timeout."""
        # Used mostly for testing
        self.__timeout: int = timeout

    def set_proxies(self: RequestsWebClient, proxies: dict[str, str]) -> None:
        """Set proxies from dictionary.

        * keys are schemes, e.g. "http" or "https";
        * values are "scheme://user:password@host:port/".

        For example:
            proxies = {'http': 'http://user:pass@10.10.1.10:3128/'}
        """
        # Used mostly for testing
        self.__proxies: dict[str, str] = proxies

    def set_max_response_data_length(
        self: RequestsWebClient,
        max_response_data_length: int,
    ) -> None:
        """Set maximum length of response data.

        Args:
            max_response_data_length: Maximum length of response data.
        """
        self.__max_response_data_length = max_response_data_length

    def get(self: RequestsWebClient, url: str) -> AbstractWebClientResponse:
        """GET a URL.

        Args:
            self: Instance.
            url: URL to GET.

        Returns:
            Response object.
        """
        try:
            response: requests.Response = requests.get(
                url,
                timeout=self.__timeout,
                stream=True,
                headers={"User-Agent": self.__USER_AGENT},
                proxies=self.__proxies,
            )
        except requests.exceptions.Timeout as ex:
            # Retryable timeouts
            return RequestsWebClientErrorResponse(message=str(ex), retryable=True)

        except requests.exceptions.RequestException as ex:
            # Other errors, e.g. redirect loops
            return RequestsWebClientErrorResponse(message=str(ex), retryable=False)

        else:
            if 200 <= response.status_code < 300:  # noqa: PLR2004
                return RequestsWebClientSuccessResponse(
                    requests_response=response,
                    max_response_data_length=self.__max_response_data_length,
                )

            message: str = f"{response.status_code} {response.reason}"
            if response.status_code in RETRYABLE_HTTP_STATUS_CODES:
                return RequestsWebClientErrorResponse(message=message, retryable=True)

            return RequestsWebClientErrorResponse(message=message, retryable=False)
