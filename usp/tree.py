"""Helpers to generate a sitemap tree."""


from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import ParseResult, urljoin, urlparse

from loguru import logger as log

from .exceptions import SitemapExceptionError
from .fetch_parse import SitemapFetcher
from .helpers import is_http_url
from .objects.sitemap import (
    AbstractSitemap,
    IndexRobotsTxtSitemap,
    IndexWebsiteSitemap,
    InvalidSitemap,
)

if TYPE_CHECKING:
    from .web_client.abstract_client import AbstractWebClient

# Paths which are not exposed in robots.txt but might still contain a sitemap.
_UNPUBLISHED_SITEMAP_PATHS: set[str] = {
    "sitemap.xml",
    "sitemap.xml.gz",
    "sitemap_index.xml",
    "sitemap-index.xml",
    "sitemap_index.xml.gz",
    "sitemap-index.xml.gz",
    ".sitemap.xml",
    "sitemap",
    "admin/config/search/xmlsitemap",
    "sitemap/sitemap-index.xml",
    "sitemap_news.xml",
    "sitemap-news.xml",
    "sitemap_news.xml.gz",
    "sitemap-news.xml.gz",
}


def sitemap_tree_for_homepage(
    homepage_url: str,
    web_client: AbstractWebClient | None = None,
) -> AbstractSitemap:
    """Using a homepage URL, fetch the tree of sitemaps and pages listed in them.

    Args:
        homepage_url: Homepage URL of a website to fetch the sitemap tree for, e.g. "http://www.example.com/".
        web_client: Web client implementation to use for fetching sitemaps.

    Raises:
        SitemapException: If the homepage URL is not a HTTP(s) URL.

    Returns:
        Root sitemap object of the fetched sitemap tree.
    """
    if not is_http_url(homepage_url):
        msg: str = f"URL {homepage_url} is not a HTTP(s) URL."
        raise SitemapExceptionError(msg)

    parse_result: ParseResult = urlparse(homepage_url)
    stripped_homepage_url: str = parse_result.scheme + "://" + parse_result.netloc + "/"
    if homepage_url != stripped_homepage_url:
        log.warning(f"Assuming that the homepage of {homepage_url} is {stripped_homepage_url}")
        homepage_url = stripped_homepage_url

    robots_txt_url: str = urljoin(homepage_url, "robots.txt")

    sitemaps = []

    robots_txt_fetcher = SitemapFetcher(
        url=robots_txt_url,
        web_client=web_client,
        recursion_level=0,
    )
    robots_txt_sitemap: AbstractSitemap = robots_txt_fetcher.sitemap()
    sitemaps.append(robots_txt_sitemap)

    sitemap_urls_found_in_robots_txt = set()
    if isinstance(robots_txt_sitemap, IndexRobotsTxtSitemap):
        for sub_sitemap in robots_txt_sitemap.sub_sitemaps:
            sitemap_urls_found_in_robots_txt.add(sub_sitemap.url)

    for unpublished_sitemap_path in _UNPUBLISHED_SITEMAP_PATHS:
        unpublished_sitemap_url: str = homepage_url + unpublished_sitemap_path

        # Don't refetch URLs already found in robots.txt
        if unpublished_sitemap_url not in sitemap_urls_found_in_robots_txt:
            unpublished_sitemap_fetcher = SitemapFetcher(
                url=unpublished_sitemap_url,
                web_client=web_client,
                recursion_level=0,
            )
            unpublished_sitemap: AbstractSitemap = unpublished_sitemap_fetcher.sitemap()

            # Skip the ones that weren't found
            if not isinstance(unpublished_sitemap, InvalidSitemap):
                sitemaps.append(unpublished_sitemap)

    return IndexWebsiteSitemap(url=homepage_url, sub_sitemaps=sitemaps)
