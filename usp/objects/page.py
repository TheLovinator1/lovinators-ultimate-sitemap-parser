"""Objects that represent a page found in one of the sitemaps."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum, unique
from typing import TYPE_CHECKING, Self

if TYPE_CHECKING:
    import datetime

# Default sitemap page priority, as per the spec.
SITEMAP_PAGE_DEFAULT_PRIORITY = Decimal("0.5")


class SitemapNewsStory:
    """Single story derived from Google News XML sitemap."""

    __slots__: list[str] = [
        "__title",
        "__publish_date",
        "__publication_name",
        "__publication_language",
        "__access",
        "__genres",
        "__keywords",
        "__stock_tickers",
    ]

    def __init__(  # noqa: PLR0913
        self: Self,
        title: str,
        publish_date: datetime.datetime,
        publication_name: str | None = None,
        publication_language: str | None = None,
        access: str | None = None,
        genres: list[str] | None = None,
        keywords: list[str] | None = None,
        stock_tickers: list[str] | None = None,
    ) -> None:
        """Initialize a new Google News story.

        Args:
            self: Single story derived from Google News XML sitemap.
            title: Story title.
            publish_date: Story publication date.
            publication_name: Name of the news publication in which the article appears in.
            publication_language: Primary language of the news publication in which the article appears in.
            access: Accessibility of the article.
            genres: List of properties characterizing the content of the article. Defaults to None.
            keywords: List of keywords describing the topic of the article. Defaults to None.
            stock_tickers: List of up to 5 stock tickers that are the main subject of the article. Defaults to None.
        """  # noqa: E501
        # Spec defines that some of the properties below are "required" but in practice
        # not every website provides the required properties. So, we require only
        # "title" and "publish_date" to be set.

        self.__title: str = title
        self.__publish_date: datetime.datetime = publish_date
        self.__publication_name: str | None = publication_name
        self.__publication_language: str | None = publication_language
        self.__access: str | None = access
        self.__genres: list[str] = genres or []
        self.__keywords: list[str] = keywords or []
        self.__stock_tickers: list[str] = stock_tickers or []

    def __eq__(self: SitemapNewsStory, other: SitemapNewsStory) -> bool:  # noqa: PLR0911
        """Return True if Google News stories are equal.

        Args:
            self: Single story derived from Google News XML sitemap.
            other: Single story derived from Google News XML sitemap.

        Raises:
            NotImplementedError: If other is not a SitemapNewsStory.

        Returns:
            True if Google News stories are equal.
        """
        if not isinstance(other, SitemapNewsStory):
            raise NotImplementedError

        if self.title != other.title:
            return False

        if self.publish_date != other.publish_date:
            return False

        if self.publication_name != other.publication_name:
            return False

        if self.publication_language != other.publication_language:
            return False

        if self.access != other.access:
            return False

        if self.genres != other.genres:
            return False

        if self.keywords != other.keywords:
            return False

        if self.stock_tickers != other.stock_tickers:
            return False

        return True

    def __hash__(self: SitemapNewsStory) -> int:
        """Return hash of the object."""
        return hash(
            (
                self.title,
                self.publish_date,
                self.publication_name,
                self.publication_language,
                self.access,
                self.genres,
                self.keywords,
                self.stock_tickers,
            ),
        )

    def __repr__(self: SitemapNewsStory) -> str:
        """Return string representation of the object."""
        return (
            f"{self.__class__.__name__}("
            f"title={self.title}, "
            f"publish_date={self.publish_date}, "
            f"publication_name={self.publication_name}, "
            f"publication_language={self.publication_language}, "
            f"access={self.access}, "
            f"genres={self.genres}, "
            f"keywords={self.keywords}, "
            f"stock_tickers={self.stock_tickers}"
            ")"
        )

    @property
    def title(self: SitemapNewsStory) -> str:
        """Return story title.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            Story title.
        """
        return self.__title

    @property
    def publish_date(self: SitemapNewsStory) -> datetime.datetime:
        """Return story publication date.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            Story publication date.
        """
        return self.__publish_date

    @property
    def publication_name(self: SitemapNewsStory) -> str | None:
        """Return name of the news publication in which the article appears in.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            Name of the news publication in which the article appears in.
        """
        return self.__publication_name

    @property
    def publication_language(self: SitemapNewsStory) -> str | None:
        """Return primary language of the news publication in which the article appears in.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            Primary language of the news publication in which the article appears in.
        """  # noqa: E501
        return self.__publication_language

    @property
    def access(self: SitemapNewsStory) -> str | None:
        """Return accessibility of the article.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            Accessibility of the article.
        """
        return self.__access

    @property
    def genres(self: SitemapNewsStory) -> list[str]:
        """Return list of properties characterizing the content of the article.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            List of properties characterizing the content of the article.
        """
        return self.__genres

    @property
    def keywords(self: SitemapNewsStory) -> list[str]:
        """Return list of keywords describing the topic of the article.

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            List of keywords describing the topic of the article.
        """
        return self.__keywords

    @property
    def stock_tickers(self: SitemapNewsStory) -> list[str]:
        """Return list of up to 5 stock tickers that are the main subject of the article.

        Each ticker must be prefixed by the name of its stock exchange, and must match
        its entry in Google Finance. For example, "NASDAQ:AMAT" (but not "NASD:AMAT"),
        or "BOM:500325" (but not "BOM:RIL").

        Args:
            self: Single story derived from Google News XML sitemap.

        Returns:
            List of up to 5 stock tickers that are the main subject of the article.
        """  # noqa: E501
        return self.__stock_tickers


@unique
class SitemapPageChangeFrequency(Enum):
    """Change frequency of a sitemap URL."""

    ALWAYS = "always"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    NEVER = "never"

    @classmethod
    def has_value(cls: type[SitemapPageChangeFrequency], value: str) -> bool:
        """Test if enum has specified value."""
        return any(value == item.value for item in cls)


class SitemapPage:
    """Single sitemap-derived page."""

    __slots__: list[str] = [
        "__url",
        "__priority",
        "__last_modified",
        "__change_frequency",
        "__news_story",
    ]

    def __init__(  # noqa: PLR0913
        self: SitemapPage,
        url: str,
        priority: Decimal = SITEMAP_PAGE_DEFAULT_PRIORITY,
        last_modified: datetime.datetime | None = None,
        change_frequency: SitemapPageChangeFrequency | None = None,
        news_story: SitemapNewsStory | None = None,
    ) -> None:
        """Initialize a new sitemap-derived page.

        :param url: Page URL.
        :param priority: Priority of this URL relative to other URLs on your site.
        :param last_modified: Date of last modification of the URL.
        :param change_frequency: Change frequency of a sitemap URL.
        :param news_story: Google News story attached to the URL.
        """
        self.__url: str = url
        self.__priority: Decimal = priority
        self.__last_modified: datetime.datetime | None = last_modified
        self.__change_frequency: SitemapPageChangeFrequency | None = change_frequency
        self.__news_story: SitemapNewsStory | None = news_story

    def __eq__(self: SitemapPage, other: SitemapPage) -> bool:
        """Return True if sitemap pages are equal.

        Args:
            self: Single sitemap-derived page.
            other: Single sitemap-derived page.

        Raises:
            NotImplementedError: If other is not a SitemapPage.

        Returns:
            True if sitemap pages are equal.
        """
        if not isinstance(other, SitemapPage):
            raise NotImplementedError

        if self.url != other.url:
            return False

        if self.priority != other.priority:
            return False

        if self.last_modified != other.last_modified:
            return False

        if self.change_frequency != other.change_frequency:
            return False

        if self.news_story != other.news_story:
            return False

        return True

    def __hash__(self: SitemapPage) -> int:
        """Return hash of the object."""
        # Hash only the URL to be able to find unique pages later on
        return hash(self.url)

    def __repr__(self: SitemapPage) -> str:
        """Return string representation of the object.

        Args:
            self: Single sitemap-derived page.

        Returns:
            String representation of the object.
        """
        return (
            f"{self.__class__.__name__}("
            f"url={self.url}, "
            f"priority={self.priority}, "
            f"last_modified={self.last_modified}, "
            f"change_frequency={self.change_frequency}, "
            f"news_story={self.news_story}"
            ")"
        )

    @property
    def url(self: SitemapPage) -> str:
        """Return page URL.

        :return: Page URL.
        """
        return self.__url

    @property
    def priority(self: SitemapPage) -> Decimal:
        """Return priority of this URL relative to other URLs on your site.

        :return: Priority of this URL relative to other URLs on your site.
        """
        return self.__priority

    @property
    def last_modified(self: SitemapPage) -> datetime.datetime | None:
        """Return date of last modification of the URL.

        :return: Date of last modification of the URL.
        """
        return self.__last_modified

    @property
    def change_frequency(self: SitemapPage) -> SitemapPageChangeFrequency | None:
        """Return change frequency of a sitemap URL.

        :return: Change frequency of a sitemap URL.
        """
        return self.__change_frequency

    @property
    def news_story(self: SitemapPage) -> SitemapNewsStory | None:
        """Return Google News story attached to the URL.

        :return: Google News story attached to the URL.
        """
        return self.__news_story
