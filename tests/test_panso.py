from typing import TYPE_CHECKING

from usp.tree import sitemap_tree_for_homepage

if TYPE_CHECKING:
    from usp.objects.sitemap import AbstractSitemap


def test_sitemap_tree_for_homepage_on_panso() -> None:
    """Test sitemap_tree_for_homepage() on panso.se."""
    result: AbstractSitemap = sitemap_tree_for_homepage("https://panso.se/")
    sub_sitemaps = result.sub_sitemaps  # type: ignore  # noqa: PGH003
    assert len(sub_sitemaps) == 1
    assert sub_sitemaps[0].url == "https://panso.se/robots.txt"

    assert result
