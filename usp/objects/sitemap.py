"""Objects that represent one of the found sitemaps."""
from __future__ import annotations

import abc
import os
import pickle
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .page import SitemapPage


class AbstractSitemap(metaclass=abc.ABCMeta):
    """Abstract sitemap."""

    __slots__: list[str] = [
        "__url",
    ]

    def __init__(self: AbstractSitemap, url: str) -> None:
        """Initialize a new sitemap.

        :param url: Sitemap URL.
        """
        self.__url: str = url

    def __eq__(self: AbstractSitemap, other: AbstractSitemap) -> bool:
        """Return True if two sitemaps are equal.

        Args:
            self: The first sitemap.
            other: The second sitemap.

        Raises:
            NotImplementedError: If the other object is not a sitemap.

        Returns:
            True if two sitemaps are equal.
        """
        if not isinstance(other, AbstractSitemap):
            raise NotImplementedError

        if self.url != other.url:
            return False

        return True

    def __hash__(self: AbstractSitemap) -> int:
        """Return hash of the sitemap.

        Returns:
            Hash of the sitemap.
        """
        return hash((self.url,))

    def __repr__(self: AbstractSitemap) -> str:
        """Return string representation of the sitemap.

        Returns:
            String representation of the sitemap.
        """
        return f"{self.__class__.__name__}(url={self.url})"

    @property
    def url(self: AbstractSitemap) -> str:
        """Return sitemap URL.

        :return: Sitemap URL.
        """
        return self.__url

    @abc.abstractmethod
    def all_pages(self: AbstractSitemap) -> Iterator[SitemapPage]:
        """Return iterator which yields all pages of this sitemap and linked sitemaps (if any).

        Args:
            self: The sitemap.

        Raises:
            NotImplementedError: If the other object is not a sitemap.

        Yields:
            Iterator which yields all pages of this sitemap and linked sitemaps (if any).
        """  # noqa: E501
        msg = "Abstract method"
        raise NotImplementedError(msg)


class InvalidSitemap(AbstractSitemap):  # noqa: PLW1641
    """Invalid sitemap, e.g. the one that can't be parsed."""

    __slots__: list[str] = [
        "__reason",
    ]

    def __init__(self: InvalidSitemap, url: str, reason: str) -> None:
        """Initialize a new invalid sitemap.

        :param url: Sitemap URL.
        :param reason: Reason why the sitemap is deemed invalid.
        """
        super().__init__(url=url)
        self.__reason = reason

    def __eq__(self: InvalidSitemap, other: AbstractSitemap) -> bool:
        """Return True if two invalid sitemaps are equal.

        Args:
            self: The first invalid sitemap.
            other: The second invalid sitemap.

        Raises:
            NotImplementedError: If the other object is not an invalid sitemap.

        Returns:
            True if two invalid sitemaps are equal.
        """
        if not isinstance(other, InvalidSitemap):
            raise NotImplementedError

        if self.url != other.url:
            return False

        if self.reason != other.reason:
            return False

        return True

    def __repr__(self: InvalidSitemap) -> str:
        """Return string representation of the invalid sitemap.

        Args:
            self: The invalid sitemap.

        Returns:
            String representation of the invalid sitemap.
        """
        return f"{self.__class__.__name__}(url={self.url}, reason={self.reason})"

    @property
    def reason(self: InvalidSitemap) -> str:
        """Return reason why the sitemap is deemed invalid.

        Args:
            self: The invalid sitemap.

        Returns:
            Reason why the sitemap is deemed invalid.
        """
        return self.__reason

    def all_pages(self: InvalidSitemap) -> Iterator[SitemapPage]:  # noqa: PLR6301
        """Return iterator which yields all pages of this sitemap and linked sitemaps (if any).

        Args:
            self: The invalid sitemap.

        Yields:
            Iterator which yields all pages of this sitemap and linked sitemaps (if any).
        """  # noqa: E501
        yield from []


class AbstractPagesSitemap(AbstractSitemap, metaclass=abc.ABCMeta):  # noqa: PLW1641
    """Abstract sitemap that contains URLs to pages."""

    __slots__: list[str] = [
        "__pages_temp_file_path",
    ]

    def __init__(
        self: AbstractPagesSitemap,
        url: str,
        pages: list[SitemapPage],
    ) -> None:
        """Initialize new pages sitemap.

        :param url: Sitemap URL.
        :param pages: List of pages found in a sitemap.
        """
        super().__init__(url=url)

        temp_file, self.__pages_temp_file_path = tempfile.mkstemp()
        with os.fdopen(temp_file, "wb") as tmp:
            pickle.dump(pages, tmp, protocol=pickle.HIGHEST_PROTOCOL)

    def __del__(self: AbstractPagesSitemap) -> None:
        """Delete temporary file with pages.

        Args:
            self: The pages sitemap.
        """
        Path.unlink(Path(self.__pages_temp_file_path))

    def __eq__(self: AbstractPagesSitemap, other: AbstractSitemap) -> bool:
        """Return True if two pages sitemaps are equal.

        Args:
            self: The first pages sitemap.
            other: The second pages sitemap.

        Raises:
            NotImplementedError: If the other object is not a pages sitemap.

        Returns:
            True if two pages sitemaps are equal.
        """
        if not isinstance(other, AbstractPagesSitemap):
            raise NotImplementedError

        if self.url != other.url:
            return False

        if self.pages != other.pages:
            return False

        return True

    def __repr__(self: AbstractPagesSitemap) -> str:
        """Return string representation of the pages sitemap.

        Returns:
            String representation of the pages sitemap.
        """
        return f"{self.__class__.__name__}(url={self.url}, pages={self.pages})"

    @property
    def pages(self: AbstractPagesSitemap) -> list[SitemapPage]:
        """Return list of pages found in a sitemap.

        Args:
            self: The pages sitemap.

        Returns:
            List of pages found in a sitemap.
        """
        with Path.open(Path(self.__pages_temp_file_path), "rb") as tmp:
            return pickle.load(tmp)  # noqa: S301

    def all_pages(self: AbstractPagesSitemap) -> Iterator[SitemapPage]:
        """Return iterator which yields all pages of this sitemap and linked sitemaps (if any).

        Args:
            self: The pages sitemap.

        Yields:
            Iterator which yields all pages of this sitemap and linked sitemaps (if any).
        """  # noqa: E501
        yield from self.pages


class PagesXMLSitemap(AbstractPagesSitemap):
    """XML sitemap that contains URLs to pages."""


class PagesTextSitemap(AbstractPagesSitemap):
    """Plain text sitemap that contains URLs to pages."""


class PagesRSSSitemap(AbstractPagesSitemap):
    """RSS 2.0 sitemap that contains URLs to pages."""


class PagesAtomSitemap(AbstractPagesSitemap):
    """RSS 0.3 / 1.0 sitemap that contains URLs to pages."""


class AbstractIndexSitemap(AbstractSitemap):  # noqa: PLW1641
    """Abstract sitemap with URLs to other sitemaps."""

    __slots__: list[str] = [
        "__sub_sitemaps",
    ]

    def __init__(
        self: AbstractIndexSitemap,
        url: str,
        sub_sitemaps: list[AbstractSitemap],
    ) -> None:
        """Initialize new index sitemap.

        Args:
            self: The index sitemap.
            url: Sitemap URL.
            sub_sitemaps: Sub-sitemaps that are linked to from this sitemap.
        """
        super().__init__(url=url)
        self.__sub_sitemaps: list[AbstractSitemap] = sub_sitemaps

    def __eq__(self: AbstractIndexSitemap, other: AbstractSitemap) -> bool:
        """Return True if two index sitemaps are equal.

        Args:
            self: The first index sitemap.
            other: The second index sitemap.

        Raises:
            NotImplementedError: If the other object is not an index sitemap.

        Returns:
            True if two index sitemaps are equal.
        """
        if not isinstance(other, AbstractIndexSitemap):
            raise NotImplementedError

        if self.url != other.url:
            return False

        if self.sub_sitemaps != other.sub_sitemaps:
            return False

        return True

    def __repr__(self: AbstractIndexSitemap) -> str:
        """Return string representation of the index sitemap.

        Returns:
            String representation of the index sitemap.
        """
        return (
            f"{self.__class__.__name__}("
            f"url={self.url}, "
            f"sub_sitemaps={self.sub_sitemaps}"
            ")"
        )

    @property
    def sub_sitemaps(self: AbstractIndexSitemap) -> list[AbstractSitemap]:
        """Return sub-sitemaps that are linked to from this sitemap.

        :return: Sub-sitemaps that are linked to from this sitemap.
        """
        return self.__sub_sitemaps

    def all_pages(self: AbstractIndexSitemap) -> Iterator[SitemapPage]:
        """Return iterator which yields all pages of this sitemap and linked sitemaps (if any).

        :return: Iterator which yields all pages of this sitemap and linked sitemaps (if any).
        """  # noqa: E501
        for sub_sitemap in self.sub_sitemaps:
            yield from sub_sitemap.all_pages()


class IndexWebsiteSitemap(AbstractIndexSitemap):
    """Website's root sitemaps, including robots.txt and extra ones."""


class IndexXMLSitemap(AbstractIndexSitemap):
    """XML sitemap with URLs to other sitemaps."""


class IndexRobotsTxtSitemap(AbstractIndexSitemap):
    """robots.txt sitemap with URLs to other sitemaps."""
