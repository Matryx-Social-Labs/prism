"""safe_next: the magic link carries `next`, so the server must refuse what the
web refuses (lib/next.ts safeNext). A URL parser strips tab, CR and LF anywhere,
so "/\t/host" is "//host" to a browser; "/\\host" is protocol-relative too."""

import pytest

from api.routes.auth import safe_next


@pytest.mark.parametrize("hop", ["//evil.example", "/\\evil.example", "/\t/evil.example", "/\n/evil.example", "/\r\\evil.example", "https://evil.example/"])
def test_refuses_a_path_that_leaves_the_site(hop):
    assert safe_next(hop) is None


def test_keeps_a_same_site_path():
    assert safe_next("/story/abc?from=lens-limit") == "/story/abc?from=lens-limit"
