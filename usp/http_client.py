from __future__ import annotations

from functools import lru_cache

import httpx
from fake_useragent import UserAgent


@lru_cache(maxsize=1)
def get_useragent() -> str:
    """Return the most popular user agent string.

    Cached so that we don't have to fetch it every time as it will always be the same.

    Returns:
        Most popular user agent string.
    """
    ua = UserAgent()
    all_browsers: list[dict[str, float | str | int]] = ua.data_browsers
    all_browsers.sort(key=lambda x: x["percent"], reverse=True)
    most_popular_browser: dict[str, float | str | int] = all_browsers[0]

    most_popular_useragent: str = str(most_popular_browser["useragent"])
    return most_popular_useragent


def get_http_client() -> httpx.Client:
    """Return a HTTP client object.

    :return: HTTP client object.
    """
    return httpx.Client(
        headers={"User-Agent": get_useragent()},
        timeout=10,
        http2=True,
    )
