import datetime

import pytest

from usp.exceptions import (
    GunzipExceptionError,
    SitemapExceptionError,
    StripURLToHomepageExceptionError,
)
from usp.helpers import (
    gunzip,
    html_unescape_strip,
    is_http_url,
    parse_iso8601_date,
    parse_rfc2822_date,
    strip_url_to_homepage,
)


def test_html_unescape_strip() -> None:
    """Test html_unescape_strip() function."""
    assert html_unescape_strip("  tests &amp; tests  ") == "tests & tests"
    assert html_unescape_strip(None) is None


def test_parse_iso8601_date() -> None:
    """Test parsing ISO 8601 date (e.g. from Atom's <updated>) into datetime.datetime object."""  # noqa: E501
    # TODO: Readd all the deleted tests

    with pytest.raises(SitemapExceptionError):
        # noinspection PyTypeChecker
        parse_iso8601_date(None)  # type: ignore  # noqa: PGH003

    with pytest.raises(SitemapExceptionError):
        parse_iso8601_date("")

    assert parse_iso8601_date("1997-07-16") == datetime.datetime(  # noqa: DTZ001
        year=1997,
        month=7,
        day=16,
        tzinfo=None,
    )


def test_parse_rfc2822_date() -> None:
    """Test parsing RFC 2822 date (e.g. from Atom's <issued>) into datetime.datetime object."""  # noqa: E501
    assert parse_rfc2822_date("Tue, 10 Aug 2010 20:43:53 -0000") == datetime.datetime(
        year=2010,
        month=8,
        day=10,
        hour=20,
        minute=43,
        second=53,
        microsecond=0,
        tzinfo=datetime.timezone(datetime.timedelta(seconds=0)),
    )

    assert parse_rfc2822_date("Thu, 17 Dec 2009 12:04:56 +0200") == datetime.datetime(
        year=2009,
        month=12,
        day=17,
        hour=12,
        minute=4,
        second=56,
        microsecond=0,
        tzinfo=datetime.timezone(datetime.timedelta(seconds=7200)),
    )


# noinspection SpellCheckingInspection
def test_is_http_url() -> None:
    """Test if a string is a HTTP(s) URL."""
    # noinspection PyTypeChecker
    assert not is_http_url(None)
    assert not is_http_url("")

    assert not is_http_url("abc")
    assert not is_http_url("/abc")
    assert not is_http_url("//abc")
    assert not is_http_url("///abc")

    assert not is_http_url("gopher://gopher.floodgap.com/0/v2/vstat")
    assert not is_http_url("ftp://ftp.freebsd.org/pub/FreeBSD/")

    assert is_http_url("http://cyber.law.harvard.edu/about")
    assert is_http_url("https://github.com/mediacloud/backend")

    # URLs with port, HTTP auth, localhost
    assert is_http_url(
        "https://username:password@domain.com:12345/path?query=string#fragment",
    )
    assert is_http_url("http://localhost:9998/feed")
    assert is_http_url("http://127.0.0.1:12345/456789")
    assert is_http_url("http://127.0.00000000.1:8899/tweet_url?id=47")

    # Travis URL
    assert is_http_url(
        "http://testing-gce-286b4005-b1ae-4b1a-a0d8-faf85e39ca92:37873/gv/tests.rss",
    )

    # URLs with mistakes fixable by fix_common_url_mistakes()
    assert not is_http_url(
        "http:/www.theinquirer.net/inquirer/news/2322928/net-neutrality-rules-lie-in-tatters-as-fcc-overruled",
    )

    # UTF-8 in paths
    assert is_http_url("http://www.example.com/šiaurė.html")

    # IDN
    assert is_http_url("http://www.šiaurė.lt/šiaurė.html")
    assert is_http_url("http://www.xn--iaur-yva35b.lt/šiaurė.html")
    assert is_http_url("http://.xn--iaur-yva35b.lt") is False  # Invalid Punycode


def test_strip_url_to_homepage() -> None:
    """Test strip_url_to_homepage() function."""
    assert (
        strip_url_to_homepage("http://www.cwi.nl:80/%7Eguido/Python.html")
        == "http://www.cwi.nl:80/"
    )

    # HTTP auth
    assert (
        strip_url_to_homepage(
            "http://username:password@www.cwi.nl/page.html",
        )
        == "http://username:password@www.cwi.nl/"
    )

    # UTF-8 in paths
    assert (
        strip_url_to_homepage("http://www.example.com/šiaurė.html")
        == "http://www.example.com/"
    )

    # IDN
    assert (
        strip_url_to_homepage("https://www.šiaurė.lt/šiaurė.html")
        == "https://www.šiaurė.lt/"
    )
    assert (
        strip_url_to_homepage("http://www.xn--iaur-yva35b.lt/šiaurė.html")
        == "http://www.xn--iaur-yva35b.lt/"
    )

    with pytest.raises(StripURLToHomepageExceptionError):
        strip_url_to_homepage(None)  # type: ignore  # noqa: PGH003

    with pytest.raises(StripURLToHomepageExceptionError):
        strip_url_to_homepage("")

    with pytest.raises(StripURLToHomepageExceptionError):
        strip_url_to_homepage("not an URL")


def test_gunzip() -> None:
    """Test gunzip() function."""
    with pytest.raises(GunzipExceptionError):
        gunzip(None)  # type: ignore  # noqa: PGH003
    with pytest.raises(GunzipExceptionError):
        gunzip("")  # type: ignore  # noqa: PGH003
    with pytest.raises(GunzipExceptionError):
        gunzip(b"")
    with pytest.raises(GunzipExceptionError):
        gunzip("foo")  # type: ignore  # noqa: PGH003
    with pytest.raises(GunzipExceptionError):
        gunzip(b"foo")
