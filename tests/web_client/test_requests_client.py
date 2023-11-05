from __future__ import annotations

import socket
from http import HTTPStatus
from typing import LiteralString
from unittest import TestCase

import requests_mock

from usp.web_client.abstract_client import (
    AbstractWebClientResponse,
    AbstractWebClientSuccessResponse,
    WebClientErrorResponse,
)
from usp.web_client.requests_client import RequestsWebClient


class TestRequestsClient(TestCase):
    """Test for RequestsWebClient class.

    Args:
        TestCase: unittest's TestCase class.

    Returns:
        None
    """

    TEST_BASE_URL = "http://test-ultimate-sitemap-parser.com"  # mocked by HTTPretty
    TEST_CONTENT_TYPE = "text/html"

    __slots__: list[str] = [
        "__client",
    ]

    def setUp(self: TestRequestsClient) -> None:
        """Set up the test."""
        super().setUp()

        self.__client = RequestsWebClient()

    def test_get(self: TestRequestsClient) -> None:
        """Test get() method.

        Args:
            self: TestRequestsClient
        """
        with requests_mock.Mocker() as m:
            test_url = self.TEST_BASE_URL + "/"
            test_content = "This is a homepage."

            m.get(
                test_url,
                headers={"Content-Type": self.TEST_CONTENT_TYPE},
                text=test_content,
            )

            response: AbstractWebClientResponse = self.__client.get(test_url)

            assert response
            assert isinstance(response, AbstractWebClientSuccessResponse)
            assert response.status_code() == HTTPStatus.OK.value
            assert response.status_message() == HTTPStatus.OK.phrase
            assert response.header("Content-Type") == self.TEST_CONTENT_TYPE
            assert response.header("content-type") == self.TEST_CONTENT_TYPE
            assert response.header("nonexistent") is None
            assert response.raw_data().decode("utf-8") == test_content

    def test_get_user_agent(self: TestRequestsClient) -> None:
        """Test get() method with custom User-Agent.

        Args:
            self: TestRequestsClient

        Returns:
            None
        """
        with requests_mock.Mocker() as m:
            test_url = self.TEST_BASE_URL + "/"

            def content_user_agent(
                request,  # noqa: ANN001
                context: dict,
            ) -> str:
                context.status_code = HTTPStatus.OK.value  # type: ignore  # noqa: PGH003
                return request.headers.get("User-Agent", "unknown")

            m.get(
                test_url,
                text=content_user_agent,
            )

            response: AbstractWebClientResponse = self.__client.get(test_url)

            assert response
            assert isinstance(response, AbstractWebClientSuccessResponse)

            content: str = response.raw_data().decode("utf-8")
            assert content == "lovinators_ultimate_sitemap_parser/0.1.0"

    def test_get_not_found(self: TestRequestsClient) -> None:
        """Test get() method with 404 response."""
        with requests_mock.Mocker() as m:
            test_url = self.TEST_BASE_URL + "/404.html"

            m.get(
                test_url,
                status_code=HTTPStatus.NOT_FOUND.value,
                reason=HTTPStatus.NOT_FOUND.phrase,
                headers={"Content-Type": self.TEST_CONTENT_TYPE},
                text="This page does not exist.",
            )

            response: AbstractWebClientResponse = self.__client.get(test_url)

            self.check_response(response, if_retryable=False)

    def test_get_nonexistent_domain(self: TestRequestsClient) -> None:
        """Test get() method with non-existent domain."""
        test_url = "http://www.totallydoesnotexisthjkfsdhkfsd.com/some_page.html"

        response: AbstractWebClientResponse = self.__client.get(test_url)

        self.check_response(response, if_retryable=False)
        assert "Failed to resolve" in response.message()  # type: ignore  # noqa: PGH003

    def test_get_timeout(self: TestRequestsClient) -> None:
        """Test get() method with timeout."""
        sock = socket.socket()
        sock.bind(("", 0))
        socket_port = sock.getsockname()[1]
        assert socket_port
        sock.listen(1)

        test_timeout = 1
        test_url: str = f"http://127.0.0.1:{socket_port}/slow_page.html"

        self.__client.set_timeout(test_timeout)

        response: AbstractWebClientResponse = self.__client.get(test_url)

        sock.close()

        self.check_response(response, if_retryable=True)
        assert "Read timed out" in response.message()  # type: ignore  # noqa: PGH003

    def check_response(
        self: TestRequestsClient,  # noqa: PLR6301
        response: AbstractWebClientResponse,
        *,
        if_retryable: bool,
    ) -> None:
        """Check if response is WebClientErrorResponse.

        Args:
            self: TestRequestsClient
            response: Response to check.
            if_retryable: True if response should be retryable.
        """
        assert response
        assert isinstance(response, WebClientErrorResponse)
        assert response.retryable() is if_retryable

    def test_get_max_response_data_length(self: TestRequestsClient) -> None:
        """Test get() method with max_response_data_length set."""
        with requests_mock.Mocker() as m:
            actual_length = 1024 * 1024
            max_length = 1024 * 512

            test_url = self.TEST_BASE_URL + "/huge_page.html"
            test_content: LiteralString = "a" * actual_length

            m.get(
                test_url,
                headers={"Content-Type": self.TEST_CONTENT_TYPE},
                text=test_content,
            )

            self.__client.set_max_response_data_length(max_length)

            response: AbstractWebClientResponse = self.__client.get(test_url)

            assert response
            assert isinstance(response, AbstractWebClientSuccessResponse)

            response_length: int = len(response.raw_data())
            assert response_length == max_length
