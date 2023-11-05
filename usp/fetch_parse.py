"""Sitemap fetchers and parsers."""
from __future__ import annotations

import abc
import re
import xml.parsers.expat
from collections import OrderedDict
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from loguru import logger as log

from .exceptions import SitemapExceptionError, SitemapXMLParsingExceptionError
from .helpers import (
    get_url_retry_on_client_errors,
    html_unescape_strip,
    is_http_url,
    parse_iso8601_date,
    parse_rfc2822_date,
    ungzipped_response_content,
)
from .objects.page import (
    SITEMAP_PAGE_DEFAULT_PRIORITY,
    SitemapNewsStory,
    SitemapPage,
    SitemapPageChangeFrequency,
)
from .objects.sitemap import (
    AbstractSitemap,
    IndexRobotsTxtSitemap,
    IndexXMLSitemap,
    InvalidSitemap,
    PagesAtomSitemap,
    PagesRSSSitemap,
    PagesTextSitemap,
    PagesXMLSitemap,
)
from .web_client.abstract_client import (
    AbstractWebClient,
    AbstractWebClientResponse,
    AbstractWebClientSuccessResponse,
    WebClientErrorResponse,
)
from .web_client.requests_client import RequestsWebClient

if TYPE_CHECKING:
    from pyexpat import XMLParserType


class SitemapFetcher:
    """robots.txt / XML / plain text sitemap fetcher."""

    __MAX_SITEMAP_SIZE = 100 * 1024 * 1024
    """Max. uncompressed sitemap size.

    Spec says it might be up to 50 MB but let's go for the full 100 MB here."""

    __MAX_RECURSION_LEVEL = 10
    """Max. recursion level in iterating over sub-sitemaps."""

    __slots__: list[str] = [
        "_url",
        "_recursion_level",
        "_web_client",
    ]

    def __init__(
        self: SitemapFetcher,
        url: str,
        recursion_level: int,
        web_client: AbstractWebClient | None = None,
    ) -> None:
        """Constructor.

        Args:
            self: robots.txt / XML / plain text sitemap fetcher.
            url: URL of the sitemap to fetch.
            recursion_level: Recursion level in iterating over sub-sitemaps.
            web_client: Web client implementation to use for fetching sitemaps.

        Raises:
            SitemapException: If the URL is not a HTTP(s) URL.
            SitemapException: If the recursion level is exceeded.
        """
        if recursion_level > self.__MAX_RECURSION_LEVEL:
            msg = (
                f"Recursion level exceeded {self.__MAX_RECURSION_LEVEL} for URL {url}."
            )
            raise SitemapExceptionError(msg)

        if not is_http_url(url):
            msg: str = f"URL {url} is not a HTTP(s) URL."
            raise SitemapExceptionError(msg)

        if not web_client:
            web_client = RequestsWebClient()

        web_client.set_max_response_data_length(self.__MAX_SITEMAP_SIZE)

        self._url: str = url
        self._web_client: RequestsWebClient | AbstractWebClient = web_client
        self._recursion_level: int = recursion_level

    def sitemap(self: SitemapFetcher) -> AbstractSitemap:
        """Fetch sitemap.

        Args:
            self: robots.txt / XML / plain text sitemap fetcher.

        Returns:
            Sitemap object.
        """
        log.info(f"Fetching level {self._recursion_level} sitemap from {self._url}...")
        response: AbstractWebClientResponse = get_url_retry_on_client_errors(
            url=self._url,
            web_client=self._web_client,
        )

        if isinstance(response, WebClientErrorResponse):
            return InvalidSitemap(
                url=self._url,
                reason=f"Unable to fetch sitemap from {self._url}: {response.message()}",  # noqa: E501
            )

        if isinstance(response, AbstractWebClientSuccessResponse):
            msg = "AbstractWebClientSuccessResponse"
            log.error(msg)

        response_content: str = ungzipped_response_content(
            url=self._url,
            response=response,  # type: ignore  # noqa: PGH003
        )

        # MIME types returned in Content-Type are unpredictable, so peek into the content instead # noqa: E501
        if response_content[:20].strip().startswith("<"):
            # XML sitemap (the specific kind is to be determined later)
            parser = XMLSitemapParser(
                url=self._url,
                content=response_content,
                recursion_level=self._recursion_level,
                web_client=self._web_client,
            )

        else:  # noqa: PLR5501
            # Assume that it's some sort of a text file (robots.txt or plain text sitemap) # noqa: E501
            if self._url.endswith("/robots.txt"):
                parser = IndexRobotsTxtSitemapParser(
                    url=self._url,
                    content=response_content,
                    recursion_level=self._recursion_level,
                    web_client=self._web_client,
                )
            else:
                parser = PlainTextSitemapParser(
                    url=self._url,
                    content=response_content,
                    recursion_level=self._recursion_level,
                    web_client=self._web_client,
                )

        log.info(f"Parsing sitemap from URL {self._url}...")
        return parser.sitemap()


class AbstractSitemapParser(metaclass=abc.ABCMeta):
    """Abstract robots.txt / XML / plain text sitemap parser."""

    __slots__: list[str] = [
        "_url",
        "_content",
        "_web_client",
        "_recursion_level",
    ]

    def __init__(
        self: AbstractSitemapParser,
        url: str,
        content: str,
        recursion_level: int,
        web_client: AbstractWebClient,
    ) -> None:
        """Constructor.

        Args:
            self: Abstract robots.txt / XML / plain text sitemap parser.
            url: URL of the sitemap to parse.
            content: Content of the sitemap to parse.
            recursion_level: Recursion level in iterating over sub-sitemaps.
            web_client: Web client implementation to use for fetching sitemaps.
        """
        self._url: str = url
        self._content: str = content
        self._recursion_level: int = recursion_level
        self._web_client: AbstractWebClient = web_client

    @abc.abstractmethod
    def sitemap(self: AbstractSitemapParser) -> AbstractSitemap:
        """Parse sitemap.

        Args:
            self: Abstract robots.txt / XML / plain text sitemap parser.

        Raises:
            NotImplementedError: If the method is not implemented.

        Returns:
            Sitemap object.
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)


class IndexRobotsTxtSitemapParser(AbstractSitemapParser):
    """robots.txt index sitemap parser."""

    def __init__(
        self: IndexRobotsTxtSitemapParser,
        url: str,
        content: str,
        recursion_level: int,
        web_client: AbstractWebClient,
    ) -> None:
        """Constructor.

        Args:
            self: robots.txt index sitemap parser.
            url: URL of the sitemap to parse.
            content: Content of the sitemap to parse.
            recursion_level: Recursion level in iterating over sub-sitemaps.
            web_client: Web client implementation to use for fetching sitemaps.

        Raises:
            SitemapException: If the URL does not look like a robots.txt URL.
        """
        super().__init__(
            url=url,
            content=content,
            recursion_level=recursion_level,
            web_client=web_client,
        )

        if not self._url.endswith("/robots.txt"):
            msg: str = f"URL does not look like robots.txt URL: {self._url}"
            raise SitemapExceptionError(msg)

    def sitemap(self: IndexRobotsTxtSitemapParser) -> AbstractSitemap:
        """Parse sitemap.

        Args:
            self: robots.txt index sitemap parser.

        Returns:
            Sitemap object.
        """
        # Serves as an ordered set because we want to deduplicate URLs but also retain the order # noqa: E501
        sitemap_urls = OrderedDict()

        for robots_txt_line in self._content.splitlines():
            sitemap_match: re.Match[str] | None = re.search(
                r"^site-?map:\s*(.+?)$",
                robots_txt_line.strip().lower(),
                flags=re.IGNORECASE,
            )
            if sitemap_match:
                sitemap_url: str | Any = sitemap_match.group(1)
                if is_http_url(sitemap_url):
                    sitemap_urls[sitemap_url] = True
                else:
                    log.warning(
                        f"Sitemap URL {sitemap_url} doesn't look like an URL, skipping",
                    )

        sub_sitemaps = []

        for sitemap_url in sitemap_urls:
            fetcher = SitemapFetcher(
                url=sitemap_url,
                recursion_level=self._recursion_level,
                web_client=self._web_client,
            )
            fetched_sitemap: AbstractSitemap = fetcher.sitemap()
            sub_sitemaps.append(fetched_sitemap)

        return IndexRobotsTxtSitemap(url=self._url, sub_sitemaps=sub_sitemaps)


class PlainTextSitemapParser(AbstractSitemapParser):
    """Plain text sitemap parser."""

    def sitemap(self: PlainTextSitemapParser) -> AbstractSitemap:
        """Parse sitemap.

        Args:
            self: Plain text sitemap parser.

        Returns:
            Sitemap object.
        """
        story_urls = OrderedDict()

        for story_url in self._content.splitlines():
            stripped_story_url: str = story_url.strip()
            if not stripped_story_url:
                continue
            if is_http_url(stripped_story_url):
                story_urls[stripped_story_url] = True
            else:
                log.warning(
                    f"Story URL {stripped_story_url} doesn't look like an URL, skipping",  # noqa: E501
                )

        pages = []
        for page_url in story_urls:
            page = SitemapPage(url=page_url)
            pages.append(page)

        return PagesTextSitemap(url=self._url, pages=pages)


class XMLSitemapParser(AbstractSitemapParser):
    """XML sitemap parser."""

    __XML_NAMESPACE_SEPARATOR = " "

    __slots__: list[str] = [
        "_concrete_parser",
    ]

    def __init__(
        self: XMLSitemapParser,
        url: str,
        content: str,
        recursion_level: int,
        web_client: AbstractWebClient,
    ) -> None:
        """Constructor.

        Args:
            self: XML sitemap parser.
            url: URL of the sitemap to parse.
            content: Content of the sitemap to parse.
            recursion_level: Recursion level in iterating over sub-sitemaps.
            web_client: Web client implementation to use for fetching sitemaps.
        """
        super().__init__(
            url=url,
            content=content,
            recursion_level=recursion_level,
            web_client=web_client,
        )

        # Will be initialized when the type of sitemap is known
        self._concrete_parser = None

    def sitemap(self: XMLSitemapParser) -> AbstractSitemap:
        """Parse sitemap.

        Args:
            self: XML sitemap parser.

        Returns:
            Sitemap object.
        """
        parser: XMLParserType = xml.parsers.expat.ParserCreate(
            namespace_separator=self.__XML_NAMESPACE_SEPARATOR,
        )
        parser.StartElementHandler = self._xml_element_start
        parser.EndElementHandler = self._xml_element_end
        parser.CharacterDataHandler = self._xml_char_data

        try:
            is_final = True
            parser.Parse(self._content, is_final)
        except Exception as ex:  # noqa: BLE001
            # Some sitemap XML files might end abruptly because web servers might be
            # timing out on returning huge XML files so don't return InvalidSitemap()
            # but try to get as much pages as possible
            log.error(f"Parsing sitemap from URL {self._url} failed: {ex}")

        if not self._concrete_parser:
            return InvalidSitemap(
                url=self._url,
                reason=f"No parsers support sitemap from {self._url}",
            )

        return self._concrete_parser.sitemap()

    @classmethod
    def __normalize_xml_element_name(cls: type[XMLSitemapParser], name: str) -> str:
        """Replace namespace URL in the argument element name with internal namespace.

        * Elements from http://www.sitemaps.org/schemas/sitemap/0.9 namespace will be
          prefixed with "sitemap:", e.g. "<loc>" will become "<sitemap:loc>"

        * Elements from http://www.google.com/schemas/sitemap-news/0.9 namespace will be
          prefixed with "news:", e.g. "<publication>" will become "<news:publication>"

        For non-sitemap namespaces, return the element name with the namespace stripped.

        Args:
            cls: XML sitemap parser class.
            name: Namespace URL plus XML element name, e.g. "http://www.sitemaps.org/schemas/sitemap/0.9 loc"

        Returns:
            Normalized element name, e.g. "sitemap:loc" or "news:publication".
        """  # noqa: E501
        name_parts: list[str] = name.split(cls.__XML_NAMESPACE_SEPARATOR)

        if len(name_parts) == 1:
            namespace_url: str = ""
            name = name_parts[0]

        elif len(name_parts) == 2:  # noqa: PLR2004
            namespace_url = name_parts[0]
            name = name_parts[1]

        else:
            msg: str = f"Unable to determine namespace for element '{name}'"
            raise SitemapXMLParsingExceptionError(msg)

        if "/sitemap/" in namespace_url:
            name = f"sitemap:{name}"
        elif "/sitemap-news/" in namespace_url:
            name = f"news:{name}"
        else:
            # We don't care about the rest of the namespaces, so just keep the plain element name # noqa: E501
            pass

        return name

    def _xml_element_start(
        self: XMLSitemapParser,
        name: str,
        attrs: dict[str, str],
    ) -> None:
        name = self.__normalize_xml_element_name(name)

        if self._concrete_parser:
            self._concrete_parser.xml_element_start(name=name, attrs=attrs)

        else:  # noqa: PLR5501
            # Root element -- initialize concrete parser
            if name == "sitemap:urlset":
                self._concrete_parser = PagesXMLSitemapParser(
                    url=self._url,
                )

            elif name == "sitemap:sitemapindex":
                self._concrete_parser = IndexXMLSitemapParser(
                    url=self._url,
                    web_client=self._web_client,
                    recursion_level=self._recursion_level,
                )

            elif name == "rss":
                self._concrete_parser = PagesRSSSitemapParser(
                    url=self._url,
                )

            elif name == "feed":
                self._concrete_parser = PagesAtomSitemapParser(
                    url=self._url,
                )

            else:
                msg: str = f"Unsupported root element '{name}'."
                raise SitemapXMLParsingExceptionError(msg)

    def _xml_element_end(self: XMLSitemapParser, name: str) -> None:
        name = self.__normalize_xml_element_name(name)

        if not self._concrete_parser:
            msg = "Concrete sitemap parser should be set by now."
            raise SitemapXMLParsingExceptionError(msg)

        self._concrete_parser.xml_element_end(name=name)

    def _xml_char_data(self: XMLSitemapParser, data: str) -> None:
        if not self._concrete_parser:
            msg = "Concrete sitemap parser should be set by now."
            raise SitemapXMLParsingExceptionError(msg)

        self._concrete_parser.xml_char_data(data=data)


class AbstractXMLSitemapParser(metaclass=abc.ABCMeta):
    """Abstract XML sitemap parser."""

    __slots__: list[str] = [
        # URL of the sitemap that is being parsed
        "_url",
        # Last encountered character data
        "_last_char_data",
        "_last_handler_call_was_xml_char_data",
    ]

    def __init__(self: AbstractXMLSitemapParser, url: str) -> None:
        """Constructor.

        Args:
            self: Abstract XML sitemap parser.
            url: URL of the sitemap that is being parsed.
        """
        self._url: str = url
        self._last_char_data: str = ""
        self._last_handler_call_was_xml_char_data = False

    def xml_element_start(
        self: AbstractXMLSitemapParser,
        name: str,  # noqa: ARG002
        attrs: dict[str, str],  # noqa: ARG002
    ) -> None:
        """Handler for XML element start.

        Args:
            self: Abstract XML sitemap parser.
            name: XML element name.
            attrs: XML element attributes.
        """
        self._last_handler_call_was_xml_char_data = False

    def xml_element_end(self: AbstractXMLSitemapParser, name: str) -> None:  # noqa: ARG002
        """Handler for XML element end.

        Args:
            self: Abstract XML sitemap parser.
            name: XML element name.
        """
        # End of any element always resets last encountered character data
        self._last_char_data = ""
        self._last_handler_call_was_xml_char_data = False

    def xml_char_data(self: AbstractXMLSitemapParser, data: str) -> None:
        """Handler for XML character data.

        Args:
            self: Abstract XML sitemap parser.
            data: XML character data.
        """
        # Handler might be called multiple times for what essentially is a single
        # string, e.g. in case of entities ("ABC &amp; DEF"), so this is why
        # we're appending
        if self._last_handler_call_was_xml_char_data:
            self._last_char_data += data
        else:
            self._last_char_data = data

        self._last_handler_call_was_xml_char_data = True

    @abc.abstractmethod
    def sitemap(self: AbstractXMLSitemapParser) -> AbstractSitemap:
        """Return constructed sitemap.

        Args:
            self: Abstract XML sitemap parser.

        Raises:
            NotImplementedError: If the method is not implemented.

        Returns:
            Sitemap object.
        """
        msg = "Abstract method."
        raise NotImplementedError(msg)


class IndexXMLSitemapParser(AbstractXMLSitemapParser):
    """Index XML sitemap parser."""

    __slots__: list[str] = [
        "_web_client",
        "_recursion_level",
        # List of sub-sitemap URLs found in this index sitemap
        "_sub_sitemap_urls",
    ]

    def __init__(
        self: IndexXMLSitemapParser,
        url: str,
        web_client: AbstractWebClient,
        recursion_level: int,
    ) -> None:
        """Constructor.

        Args:
            self: Index XML sitemap parser.
            url: URL of the sitemap that is being parsed.
            web_client: Web client implementation to use for fetching sitemaps.
            recursion_level: Recursion level in iterating over sub-sitemaps.
        """
        super().__init__(url=url)

        self._web_client: AbstractWebClient = web_client
        self._recursion_level: int = recursion_level
        self._sub_sitemap_urls: list[str] = []

    def xml_element_end(self: IndexXMLSitemapParser, name: str) -> None:
        """Handler for XML element end.

        Args:
            name: XML element name.
        """
        if name == "sitemap:loc":
            sub_sitemap_url: str | None = html_unescape_strip(self._last_char_data)
            if not is_http_url(sub_sitemap_url):
                log.warning(
                    f"Sub-sitemap URL does not look like one: {sub_sitemap_url}",
                )

            elif sub_sitemap_url not in self._sub_sitemap_urls:
                self._sub_sitemap_urls.append(sub_sitemap_url)  # type: ignore # noqa: PGH003

        super().xml_element_end(name=name)

    def sitemap(self: IndexXMLSitemapParser) -> AbstractSitemap:
        """Return constructed sitemap.

        Args:
            self: Index XML sitemap parser.

        Returns:
            Sitemap object.
        """
        sub_sitemaps = []

        for sub_sitemap_url in self._sub_sitemap_urls:
            # URL might be invalid, or recursion limit might have been reached
            try:
                fetcher = SitemapFetcher(
                    url=sub_sitemap_url,
                    recursion_level=self._recursion_level + 1,
                    web_client=self._web_client,
                )
                fetched_sitemap: AbstractSitemap = fetcher.sitemap()
            except Exception as ex:  # noqa: BLE001
                fetched_sitemap = InvalidSitemap(
                    url=sub_sitemap_url,
                    reason=f"Unable to add sub-sitemap from URL {sub_sitemap_url}: {ex!s}",  # noqa: E501
                )

            sub_sitemaps.append(fetched_sitemap)

        return IndexXMLSitemap(url=self._url, sub_sitemaps=sub_sitemaps)


class PagesXMLSitemapParser(AbstractXMLSitemapParser):
    """Pages XML sitemap parser."""

    class Page:
        """Simple data class for holding various properties for a single <url> entry while parsing."""  # noqa: E501

        __slots__: list[str] = [
            "url",
            "last_modified",
            "change_frequency",
            "priority",
            "news_title",
            "news_publish_date",
            "news_publication_name",
            "news_publication_language",
            "news_access",
            "news_genres",
            "news_keywords",
            "news_stock_tickers",
        ]

        def __init__(self: PagesXMLSitemapParser.Page) -> None:
            """Constructor.

            Args:
                self: Simple data class for holding various properties for a single <url> entry while parsing.
            """  # noqa: E501
            self.url = None
            self.last_modified = None
            self.change_frequency = None
            self.priority = None
            self.news_title = None
            self.news_publish_date = None
            self.news_publication_name = None
            self.news_publication_language = None
            self.news_access = None
            self.news_genres = None
            self.news_keywords = None
            self.news_stock_tickers = None

        def __hash__(self: PagesXMLSitemapParser.Page) -> int:
            """Return hash of the object.

            Returns:
                Hash of the object.
            """
            return hash(
                (self.url),
            )

        def page(self: PagesXMLSitemapParser.Page) -> SitemapPage | None:  # noqa: C901, PLR0912, PLR0915
            """Return constructed sitemap page if one has been completed, otherwise None."""  # noqa: E501
            # Required
            url: str | None = html_unescape_strip(self.url)
            if not url:
                log.error("URL is unset")
                return None

            last_modified = html_unescape_strip(self.last_modified)
            if last_modified:
                last_modified = parse_iso8601_date(last_modified)

            change_frequency = html_unescape_strip(self.change_frequency)
            if change_frequency:
                change_frequency = change_frequency.lower()
                if SitemapPageChangeFrequency.has_value(change_frequency):
                    change_frequency = SitemapPageChangeFrequency(change_frequency)
                else:
                    log.warning("Invalid change frequency, defaulting to 'always'.")
                    change_frequency = SitemapPageChangeFrequency.ALWAYS
                if isinstance(change_frequency, SitemapPageChangeFrequency):
                    msg = "SitemapPageChangeFrequency"
                    log.error(msg)

            priority = html_unescape_strip(self.priority)
            if priority:
                priority = Decimal(priority)

                comp_zero = priority.compare(Decimal("0.0"))
                comp_one = priority.compare(Decimal("1.0"))
                if comp_zero in {
                    Decimal("0"),
                    Decimal("1") and comp_one in {Decimal("0"), Decimal("-1")},
                }:
                    # 0 <= priority <= 1
                    pass
                else:
                    log.warning(f"Priority is not within 0 and 1: {priority}")
                    priority = SITEMAP_PAGE_DEFAULT_PRIORITY

            else:
                priority = SITEMAP_PAGE_DEFAULT_PRIORITY

            news_title: str | None = html_unescape_strip(self.news_title)

            news_publish_date = html_unescape_strip(self.news_publish_date)
            if news_publish_date:
                news_publish_date = parse_iso8601_date(date_string=news_publish_date)

            news_publication_name: str | None = html_unescape_strip(
                self.news_publication_name,
            )
            news_publication_language: str | None = html_unescape_strip(
                self.news_publication_language,
            )
            news_access: str | None = html_unescape_strip(self.news_access)

            news_genres = html_unescape_strip(self.news_genres)
            if news_genres:
                news_genres = [x.strip() for x in news_genres.split(",")]
            else:
                news_genres = []

            news_keywords = html_unescape_strip(self.news_keywords)
            if news_keywords:
                news_keywords = [x.strip() for x in news_keywords.split(",")]
            else:
                news_keywords = []

            news_stock_tickers = html_unescape_strip(self.news_stock_tickers)
            if news_stock_tickers:
                news_stock_tickers = [x.strip() for x in news_stock_tickers.split(",")]
            else:
                news_stock_tickers = []

            sitemap_news_story = None
            if news_title and news_publish_date:
                sitemap_news_story = SitemapNewsStory(
                    title=news_title,
                    publish_date=news_publish_date,
                    publication_name=news_publication_name,
                    publication_language=news_publication_language,
                    access=news_access,
                    genres=news_genres,
                    keywords=news_keywords,
                    stock_tickers=news_stock_tickers,
                )

            return SitemapPage(
                url=url,
                last_modified=last_modified,  # type: ignore  # noqa: PGH003
                change_frequency=change_frequency,  # type: ignore  # noqa: PGH003
                priority=priority,
                news_story=sitemap_news_story,
            )

    __slots__: list[str] = [
        "_current_page",
        "_pages",
    ]

    def __init__(self: PagesXMLSitemapParser, url: str) -> None:
        """Constructor.

        Args:
            url: URL of the sitemap that is being parsed.
        """
        super().__init__(url=url)

        self._current_page = None
        self._pages = []

    def xml_element_start(
        self: PagesXMLSitemapParser,
        name: str,
        attrs: dict[str, str],
    ) -> None:
        """Handler for XML element start.

        Args:
            self: Pages XML sitemap parser.
            name: XML element name.
            attrs: XML element attributes.

        Raises:
            SitemapXMLParsingExceptionError: If the page is not unset by <url>.
        """
        super().xml_element_start(name=name, attrs=attrs)

        if name == "sitemap:url":
            if self._current_page:
                msg = "Page is expected to be unset by <url>."
                raise SitemapXMLParsingExceptionError(
                    msg,
                )
            self._current_page = self.Page()

    def __require_last_char_data_to_be_set(
        self: PagesXMLSitemapParser,
        name: str,
    ) -> None:
        """Raise exception if last character data is not set.

        Args:
            self: Pages XML sitemap parser.
            name: XML element name.

        Raises:
            SitemapXMLParsingExceptionError: If the last character data is not set.
        """
        if not self._last_char_data:
            msg: str = f"Character data is expected to be set at the end of <{name}>."
            raise SitemapXMLParsingExceptionError(msg)

    def xml_element_end(self: PagesXMLSitemapParser, name: str) -> None:  # noqa: C901, PLR0912
        """Handler for XML element end.

        Args:
            self: Pages XML sitemap parser.
            name: XML element name.

        Raises:
            SitemapXMLParsingExceptionError: If the page is not set by <url>.
        """
        if not self._current_page and name != "sitemap:urlset":
            msg: str = f"Page is expected to be set at the end of <{name}>."
            raise SitemapXMLParsingExceptionError(msg)

        if name == "sitemap:url":
            if self._current_page not in self._pages:
                self._pages.append(self._current_page)
            self._current_page = None

        else:  # noqa: PLR5501
            if name == "sitemap:loc":
                # Every entry must have <loc>
                self.__require_last_char_data_to_be_set(name=name)
                self._current_page.url = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "sitemap:lastmod":
                # Element might be present but character data might be empty
                self._current_page.last_modified = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "sitemap:changefreq":
                # Element might be present but character data might be empty
                self._current_page.change_frequency = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "sitemap:priority":
                # Element might be present but character data might be empty
                self._current_page.priority = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:name":  # news/publication/name
                # Element might be present but character data might be empty
                self._current_page.news_publication_name = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:language":  # news/publication/language
                # Element might be present but character data might be empty
                self._current_page.news_publication_language = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:publication_date":
                # Element might be present but character data might be empty
                self._current_page.news_publish_date = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:title":
                # Every Google News sitemap entry must have <title>
                self.__require_last_char_data_to_be_set(name=name)
                self._current_page.news_title = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:access":
                # Element might be present but character data might be empty
                self._current_page.news_access = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:keywords":
                # Element might be present but character data might be empty
                self._current_page.news_keywords = self._last_char_data  # type: ignore  # noqa: PGH003

            elif name == "news:stock_tickers":
                # Element might be present but character data might be empty
                self._current_page.news_stock_tickers = self._last_char_data  # type: ignore  # noqa: PGH003

        super().xml_element_end(name=name)

    def sitemap(self: PagesXMLSitemapParser) -> AbstractSitemap:
        """Return constructed sitemap.

        Returns:
            Sitemap object.
        """
        pages = []

        for page_row in self._pages:
            page = page_row.page()
            if page:
                pages.append(page)

        return PagesXMLSitemap(url=self._url, pages=pages)


class PagesRSSSitemapParser(AbstractXMLSitemapParser):
    """Pages RSS 2.0 sitemap parser.

    https://validator.w3.org/feed/docs/rss2.html
    """

    class Page:
        """Data class for holding various properties for a single RSS <item> while parsing."""  # noqa: E501

        __slots__: list[str] = [
            "link",
            "title",
            "description",
            "publication_date",
        ]

        def __init__(self: PagesRSSSitemapParser.Page) -> None:
            """Constructor.

            Args:
                self: Data class for holding various properties for a single RSS <item> while parsing.
            """  # noqa: E501
            self.link: str | None = None
            self.title: str | None = None
            self.description: str | None = None
            self.publication_date: str | None = None

        def __hash__(self: PagesRSSSitemapParser.Page) -> int:
            """Return hash of the object.

            Args:
                self: Data class for holding various properties for a single RSS <item> while parsing.

            Returns:
                Hash of the object.
            """  # noqa: E501
            return hash(
                (
                    # Hash only the URL
                    self.link,
                ),
            )

        def page(self: PagesRSSSitemapParser.Page) -> SitemapPage | None:
            """Return constructed sitemap page if one has been completed, otherwise None."""  # noqa: E501
            # Required
            link: str | None = html_unescape_strip(self.link)
            if not link:
                log.error("Link is unset")
                return None

            title: str | None = html_unescape_strip(self.title)
            description: str | None = html_unescape_strip(self.description)
            if not (title or description):
                log.error("Both title and description are unset")
                return None

            publication_date = html_unescape_strip(self.publication_date)
            if publication_date:
                publication_date = parse_rfc2822_date(publication_date)

            return SitemapPage(
                url=link,
                news_story=SitemapNewsStory(
                    title=title or description,  # type: ignore  # noqa: PGH003
                    publish_date=publication_date,  # type: ignore  # noqa: PGH003
                ),
            )

    __slots__: list[str] = [
        "_current_page",
        "_pages",
    ]

    def __init__(self: PagesRSSSitemapParser, url: str) -> None:
        """Constructor.

        Args:
            url: URL of the sitemap that is being parsed.
        """
        super().__init__(url=url)

        self._current_page = None
        self._pages = []

    def xml_element_start(
        self: PagesRSSSitemapParser,
        name: str,
        attrs: dict[str, str],
    ) -> None:
        """Handler for XML element start.

        Args:
            name: XML element name.
            attrs: XML element attributes.

        Raises:
            SitemapXMLParsingException: If <item> is encountered while already within <item>.
        """  # noqa: E501
        super().xml_element_start(name=name, attrs=attrs)

        if name == "item":
            if self._current_page:
                msg = "Page is expected to be unset by <item>."
                raise SitemapXMLParsingExceptionError(
                    msg,
                )
            self._current_page = self.Page()

    def __require_last_char_data_to_be_set(
        self: PagesRSSSitemapParser,
        name: str,
    ) -> None:
        """Check that character data is set.

        Args:
            name: XML element name.

        Raises:
            SitemapXMLParsingException: If character data is not set.
        """
        if not self._last_char_data:
            msg: str = f"Character data is expected to be set at the end of <{name}>."
            raise SitemapXMLParsingExceptionError(msg)

    def xml_element_end(self: PagesRSSSitemapParser, name: str) -> None:
        """Handler for XML element end.

        Args:
            name: XML element name.
        """
        # If within <item> already
        if self._current_page:
            if name == "item":
                if self._current_page not in self._pages:
                    self._pages.append(self._current_page)
                self._current_page = None

            else:  # noqa: PLR5501
                if name == "link":
                    # Every entry must have <link>
                    self.__require_last_char_data_to_be_set(name=name)
                    self._current_page.link = self._last_char_data

                elif name == "title":
                    # Title (if set) can't be empty
                    self.__require_last_char_data_to_be_set(name=name)
                    self._current_page.title = self._last_char_data

                elif name == "description":
                    # Description (if set) can't be empty
                    self.__require_last_char_data_to_be_set(name=name)
                    self._current_page.description = self._last_char_data

                elif name == "pubDate":
                    # Element might be present but character data might be empty
                    self._current_page.publication_date = self._last_char_data

        super().xml_element_end(name=name)

    def sitemap(self: PagesRSSSitemapParser) -> AbstractSitemap:
        """Return constructed sitemap.

        Returns:
            Sitemap object.
        """
        pages = []

        for page_row in self._pages:
            page = page_row.page()
            if page:
                pages.append(page)

        return PagesRSSSitemap(url=self._url, pages=pages)


class PagesAtomSitemapParser(AbstractXMLSitemapParser):
    """Pages Atom 0.3 / 1.0 sitemap parser.

    https://github.com/simplepie/simplepie-ng/wiki/Spec:-Atom-0.3
    https://www.ietf.org/rfc/rfc4287.txt
    http://rakaz.nl/2005/07/moving-from-atom-03-to-10.html
    """

    # TODO: merge with RSS parser class as there are too many similarities

    class Page:
        """Data class for holding various properties for a single Atom <entry> while parsing."""  # noqa: E501

        __slots__: list[str] = [
            "link",
            "title",
            "description",
            "publication_date",
        ]

        def __init__(self: PagesAtomSitemapParser.Page) -> None:
            """Constructor."""
            self.link: str | None = None
            self.title: str | None = None
            self.description: str | None = None
            self.publication_date = None

        def __hash__(self: PagesAtomSitemapParser.Page) -> int:
            """Return hash of the object.

            Args:
                self: Data class for holding various properties for a single Atom <entry> while parsing.

            Returns:
                Hash of the object.
            """  # noqa: E501
            return hash(
                (
                    # Hash only the URL
                    self.link,
                ),
            )

        def page(self: PagesAtomSitemapParser.Page) -> SitemapPage | None:
            """Return constructed sitemap page if one has been completed, otherwise None."""  # noqa: E501
            # Required
            link: str | None = html_unescape_strip(self.link)
            if not link:
                log.error("Link is unset")
                return None

            title: str | None = html_unescape_strip(self.title)
            description: str | None = html_unescape_strip(self.description)
            if not (title or description):
                log.error("Both title and description are unset")
                return None

            publication_date = html_unescape_strip(self.publication_date)
            if publication_date:
                publication_date = parse_rfc2822_date(publication_date)

            return SitemapPage(
                url=link,
                news_story=SitemapNewsStory(
                    title=title or description,  # type: ignore  # noqa: PGH003
                    publish_date=publication_date,  # type: ignore  # noqa: PGH003
                ),
            )

    __slots__: list[str] = [
        "_current_page",
        "_pages",
        "_last_link_rel_self_href",
    ]

    def __init__(self: PagesAtomSitemapParser, url: str) -> None:
        """Constructor.

        Args:
            url: URL of the sitemap that is being parsed.
        """
        super().__init__(url=url)

        self._current_page = None
        self._pages = []
        self._last_link_rel_self_href = None

    def xml_element_start(
        self: PagesAtomSitemapParser,
        name: str,
        attrs: dict[str, str],
    ) -> None:
        """Handler for XML element start.

        Args:
            self: Pages Atom 0.3 / 1.0 sitemap parser.
            name: XML element name.
            attrs: XML element attributes.

        Raises:
            SitemapXMLParsingException: If <entry> is encountered while already within <entry>.
        """  # noqa: E501
        super().xml_element_start(name=name, attrs=attrs)

        if name == "entry":
            if self._current_page:
                msg = "Page is expected to be unset by <entry>."
                raise SitemapXMLParsingExceptionError(
                    msg,
                )
            self._current_page = self.Page()

        elif name == "link":
            if self._current_page and (
                attrs.get("rel", "self").lower() == "self"
                or self._last_link_rel_self_href is None
            ):
                self._last_link_rel_self_href: str | None = attrs.get("href")

    def __require_last_char_data_to_be_set(
        self: PagesAtomSitemapParser,
        name: str,
    ) -> None:
        if not self._last_char_data:
            msg: str = f"Character data is expected to be set at the end of <{name}>."
            raise SitemapXMLParsingExceptionError(msg)

    def xml_element_end(self: PagesAtomSitemapParser, name: str) -> None:
        """Handler for XML element end.

        Args:
            self: Pages Atom 0.3 / 1.0 sitemap parser.
            name: XML element name.
        """
        # If within <entry> already
        if self._current_page:
            if name == "entry":
                if self._last_link_rel_self_href:
                    self._current_page.link = self._last_link_rel_self_href
                    self._last_link_rel_self_href = None

                    if self._current_page not in self._pages:
                        self._pages.append(self._current_page)

                self._current_page = None

            else:  # noqa: PLR5501
                if name == "title":
                    # Title (if set) can't be empty
                    self.__require_last_char_data_to_be_set(name=name)
                    self._current_page.title = self._last_char_data

                elif name in {"tagline", "summary"}:
                    # Description (if set) can't be empty
                    self.__require_last_char_data_to_be_set(name=name)
                    self._current_page.description = self._last_char_data

                elif name in {"issued", "published"}:
                    # Element might be present but character data might be empty
                    self._current_page.publication_date = self._last_char_data  # type: ignore  # noqa: PGH003

                elif name == "updated":
                    # No 'issued' or 'published' were set before
                    if not self._current_page.publication_date:
                        self._current_page.publication_date = self._last_char_data  # type: ignore  # noqa: PGH003

        super().xml_element_end(name=name)

    def sitemap(self: PagesAtomSitemapParser) -> AbstractSitemap:
        """Return constructed sitemap.

        Returns:
            Sitemap object.
        """
        pages = []

        for page_row in self._pages:
            page = page_row.page()
            if page:
                pages.append(page)

        return PagesAtomSitemap(url=self._url, pages=pages)
