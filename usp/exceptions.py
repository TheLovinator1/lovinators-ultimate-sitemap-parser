"""Exceptions used by the sitemap parser."""

from __future__ import annotations


class SitemapExceptionError(Exception):
    """Problem due to which we can't run further, e.g. wrong input parameters."""


class SitemapXMLParsingExceptionError(Exception):
    """XML parsing exception to be handled gracefully."""


class GunzipExceptionError(Exception):
    """gunzip() exception."""


class StripURLToHomepageExceptionError(Exception):
    """strip_url_to_homepage() exception."""
