from __future__ import annotations

import gzip as gzip_lib

# TODO: various exotic properties
# TODO: XML vulnerabilities with Expat
# TODO: max. recursion level
# TODO: tests responses that are too big


def gzip(data: str | bytes) -> bytes:
    """Gzip data."""
    if data is None:
        msg = "Data is None."
        raise Exception(msg)  # noqa: TRY002 # sourcery skip: raise-specific-error

    if isinstance(data, str):
        data = data.encode("utf-8")

    if not isinstance(data, bytes):
        msg = "Data is not bytes."
        raise TypeError(msg)

    try:
        gzipped_data: bytes = gzip_lib.compress(data, compresslevel=9)
    except Exception as ex:  # noqa: BLE001
        raise Exception("Unable to gzip data: %s" % str(ex)) from ex  # noqa: TRY002

    if gzipped_data is None:
        msg = "Gzipped data is None."
        raise TypeError(msg)

    if not isinstance(gzipped_data, bytes):
        msg = "Gzipped data is not bytes."
        raise TypeError(msg)

    return gzipped_data
