# Website sitemap parser for Python 3.12

## Features

- Supports all sitemap formats:
  - [XML sitemaps](https://www.sitemaps.org/protocol.html#xmlTagDefinitions)
  - [Google News sitemaps](https://support.google.com/news/publisher-center/answer/74288?hl=en)
  - [plain text sitemaps](https://www.sitemaps.org/protocol.html#otherformats)
  - [RSS 2.0 / Atom 0.3 / Atom 1.0 sitemaps](https://www.sitemaps.org/protocol.html#otherformats)
  - [Sitemaps linked from robots.txt](https://developers.google.com/search/reference/robots_txt#sitemap)
- Field-tested with ~1 million URLs as part of the [Media Cloud project](https://mediacloud.org/)
- Error-tolerant with more common sitemap bugs
- Tries to find sitemaps not listed in `robots.txt`
- Uses fast and memory-efficient Expat XML parsing
- Doesn't consume much memory even with massive sitemap hierarchies
- Provides a generated sitemap tree as an easy-to-use object tree
- Supports using a custom web client
- Uses a small number of actively maintained third-party modules
- Reasonably tested

## Installation

```sh
pip install ultimate-sitemap-parser
```

## Usage

```python
    from usp.tree import sitemap_tree_for_homepage

    tree = sitemap_tree_for_homepage('https://www.nytimes.com/')
    print(tree)
```

`sitemap_tree_for_homepage()` will return a tree of `AbstractSitemap` subclass objects that represent the sitemap
hierarchy found on the website; see a [reference of AbstractSitemap subclasses](https://ultimate-sitemap-parser.readthedocs.io/en/latest/usp.objects.html#module-usp.objects.sitemap)

If you'd like to just list all the pages found in all of the sitemaps within the website, consider using `all_pages()` method:

```python
    # all_pages() returns an Iterator
    for page in tree.all_pages():
        print(page)
```

`all_pages()` method will return an iterator yielding `SitemapPage` objects; see a [reference of SitemapPage](https://ultimate-sitemap-parser.readthedocs.io/en/latest/usp.objects.html#module-usp.objects.page)
