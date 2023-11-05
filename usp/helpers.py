"""Helper utilities."""


from __future__ import annotations

import gzip as gzip_lib
import html
import re
import time
from typing import TYPE_CHECKING
from urllib.parse import ParseResult, unquote_plus, urlparse, urlunparse

from dateutil.parser import parse as dateutil_parse
from loguru import logger as log

from .exceptions import (
    GunzipExceptionError,
    SitemapExceptionError,
    StripURLToHomepageExceptionError,
)
from .web_client.abstract_client import (
    AbstractWebClient,
    AbstractWebClientResponse,
    AbstractWebClientSuccessResponse,
    WebClientErrorResponse,
)

if TYPE_CHECKING:
    import datetime

# Regular expression to match HTTP(s) URLs.
__URL_REGEX: re.Pattern[str] = re.compile(
    r"^https?://[^\s/$.?#].[^\s]*$",
    re.IGNORECASE,
)


def is_http_url(url: str | None) -> bool:  # noqa: PLR0911
    """Returns true if URL is of the "http" ("https") scheme.

    :param url: URL to test.
    :return: True if argument URL is of the "http" ("https") scheme.
    """
    if not url:
        log.debug("URL is None or empty")
        return False

    log.debug(f"Testing if URL '{url}' is HTTP(s) URL")

    if not re.search(__URL_REGEX, url):
        log.debug(f"URL '{url}' does not match URL's regexp")
        return False

    try:
        # Try parsing the URL
        uri: ParseResult = urlparse(url)
        _: str = urlunparse(uri)

    except Exception as ex:  # noqa: BLE001
        log.debug(f"Cannot parse URL {url}: {ex}")
        return False

    if not uri.scheme:
        log.debug(f"Scheme is undefined for URL {url}.")
        return False
    if uri.scheme.lower() not in {"http", "https"}:
        log.debug(f"Scheme is not HTTP(s) for URL {url}.")
        return False
    if not uri.hostname:
        log.debug(f"Host is undefined for URL {url}.")
        return False

    return True


def html_unescape_strip(string: str | None) -> str | None:
    """Unescape HTML entities and strip string.

    Args:
        string: String to unescape and strip.

    Returns:
        Unescaped and stripped string.
    """
    if string:
        string = html.unescape(string)
        string = string.strip() or None
    return string


def parse_iso8601_date(date_string: str) -> datetime.datetime:
    """Parse ISO 8601 date (e.g. from Atom's <updated>) into datetime.datetime object.

    Args:
        date_string: ISO 8601 date, e.g. "2010-08-10T20:43:53Z".

    Raises:
        SitemapException: If the date string is unset.

    Returns:
        Datetime object of a parsed date.
    """
    # TODO: parse known date formats faster

    if not date_string:
        msg = "Date string is unset."
        raise SitemapExceptionError(msg)

    return dateutil_parse(date_string)


def parse_rfc2822_date(date_string: str) -> datetime.datetime:
    """Parse RFC 2822 date (e.g. from Atom's <issued>) into datetime.datetime object.

    :param date_string: RFC 2822 date, e.g. "Tue, 10 Aug 2010 20:43:53 -0000".
    :return: datetime.datetime object of a parsed date.
    """
    # TODO: parse known date formats faster
    return parse_iso8601_date(date_string)


def get_url_retry_on_client_errors(
    url: str,
    web_client: AbstractWebClient,
    retry_count: int = 5,
    sleep_between_retries: int = 1,
) -> AbstractWebClientResponse:
    """Fetch URL, retry on retryable errors.

    :param url: URL to fetch.
    :param web_client: Web client object to use for fetching.
    :param retry_count: How many times to retry fetching the same URL.
    :param sleep_between_retries: How long to sleep between retries, in seconds.
    :return: Web client response object.
    """
    # if retry_count > 0:
    #    msg = "Retry count must be positive."
    #    raise ValueError(msg)

    response = AbstractWebClientResponse()
    for _retry in range(retry_count):
        log.info(f"Fetching URL {url}...")
        response: AbstractWebClientResponse = web_client.get(url)

        if isinstance(response, WebClientErrorResponse):
            log.warning(f"Request for URL {url} failed: {response.message()}")

            if response.retryable():
                log.info(f"Retrying URL {url} in {sleep_between_retries} seconds...")
                time.sleep(sleep_between_retries)

            else:
                log.info(f"Not retrying for URL {url}")
                return response

        else:
            return response

    log.info(f"Giving up on URL {url}")
    return response


def __response_is_gzipped_data(
    url: str,
    response: AbstractWebClientSuccessResponse,
) -> bool:
    """Return True if Response looks like it's gzipped.

    :param url: URL the response was fetched from.
    :param response: Response object.
    :return: True if response looks like it might contain gzipped data.
    """
    uri: ParseResult = urlparse(url)
    url_path: str = unquote_plus(uri.path)
    content_type: str = response.header("content-type") or ""

    return bool(url_path.lower().endswith(".gz") or "gzip" in content_type.lower())


def gunzip(data: bytes) -> bytes:
    """Gunzip data.

    :param data: Gzipped data.
    :return: Gunzipped data.
    """
    if data is None:
        msg = "Data is None."
        raise GunzipExceptionError(msg)

    if not isinstance(data, bytes):
        raise GunzipExceptionError("Data is not bytes: %s" % str(data))

    if len(data) == 0:
        msg = "Data is empty (no way an empty string is a valid Gzip archive)."
        raise GunzipExceptionError(
            msg,
        )

    try:
        gunzipped_data = gzip_lib.decompress(data)
    except Exception as ex:
        raise GunzipExceptionError("Unable to gunzip data: %s" % str(ex))

    if gunzipped_data is None:
        msg = "Gunzipped data is None."
        raise GunzipExceptionError(msg)

    if not isinstance(gunzipped_data, bytes):
        msg = "Gunzipped data is not bytes."
        raise GunzipExceptionError(msg)

    return gunzipped_data


def ungzipped_response_content(
    url: str,
    response: AbstractWebClientSuccessResponse,
) -> str:
    """Return HTTP response's decoded content, gunzip it if necessary.

    :param url: URL the response was fetched from.
    :param response: Response object.
    :return: Decoded and (if necessary) gunzipped response string.
    """
    data = response.raw_data()

    if __response_is_gzipped_data(url=url, response=response):
        try:
            data = gunzip(data)
        except GunzipExceptionError as ex:
            # In case of an error, just assume that it's one of the non-gzipped sitemaps with ".gz" extension # noqa: E501
            msg: str = f"Unable to gunzip response {response}, maybe it's a non-gzipped sitemap: {ex}"  # noqa: E501
            log.error(msg)

    # TODO: other encodings
    data = data.decode("utf-8-sig", errors="replace")

    if isinstance(data, str):
        msg = "Decoded data is not bytes."
        log.error(msg)

    return data


def strip_url_to_homepage(url: str) -> str:
    """Strip URL to its homepage.

    :param url: URL to strip, e.g. "http://www.example.com/page.html".
    :return: Stripped homepage URL, e.g. "http://www.example.com/"
    """
    if not url:
        msg = "URL is empty."
        raise StripURLToHomepageExceptionError(msg)

    try:
        uri = urlparse(url)
        if not uri.scheme:
            msg = f"Scheme is undefined for URL {url}"
            raise StripURLToHomepageExceptionError(msg)  # noqa: TRY301

        if uri.scheme.lower() not in {"http", "https"}:
            msg: str = f"Scheme is not HTTP(s) for URL {url}"
            raise ValueError(msg)  # noqa: TRY301

        uri: tuple[str, str, str, str, str, str] = (
            uri.scheme,
            uri.netloc,
            "/",  # path
            "",  # params
            "",  # query
            "",  # fragment
        )
        url = urlunparse(uri)
    except Exception as ex:  # noqa: BLE001
        msg = f"Unable to parse URL {url}: {ex}"
        raise StripURLToHomepageExceptionError(msg) from ex

    return url
