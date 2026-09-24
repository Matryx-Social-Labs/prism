"""CSP violation reports land in the API logs while the policy is report-only.

web/next.config.ts sends Content-Security-Policy-Report-Only with report-uri
/api/v1/csp-report. Pinned: a report is logged as one compact line with the
directive, the blocked host and the page; a malformed body is dropped quietly;
and the endpoint, public by nature, cannot be used to flood the logs.
"""

import json

import pytest
from httpx import ASGITransport, AsyncClient
from structlog.testing import capture_logs

import api.routes.meta as meta

pytestmark = pytest.mark.asyncio(loop_scope="session")

REPORT = {"csp-report": {"document-uri": "https://www.readprism.news/story/x", "violated-directive": "script-src",
                         "effective-directive": "script-src-elem", "blocked-uri": "https://evil.example/x.js"}}


def _client():
    from api.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest.fixture(autouse=True)
def _fresh_window():
    meta._csp_window[:] = [0.0, 0]
    yield
    meta._csp_window[:] = [0.0, 0]


async def test_a_violation_is_logged_in_one_compact_line():
    async with _client() as c:
        with capture_logs() as logs:
            r = await c.post("/api/v1/csp-report", content=json.dumps(REPORT), headers={"Content-Type": "application/csp-report"})
    assert r.status_code == 204
    [line] = [x for x in logs if x["event"] == "csp_violation"]
    assert line["directive"] == "script-src-elem" and line["blocked"] == "https://evil.example/x.js"
    assert line["page"] == "https://www.readprism.news/story/x"


async def test_a_malformed_body_is_dropped_and_the_log_cannot_be_flooded():
    async with _client() as c:
        assert (await c.post("/api/v1/csp-report", content=b"not json")).status_code == 204
        with capture_logs() as logs:
            for _ in range(meta.CSP_LOGS_PER_MINUTE + 20):
                await c.post("/api/v1/csp-report", content=json.dumps(REPORT))
    assert len([x for x in logs if x["event"] == "csp_violation"]) <= meta.CSP_LOGS_PER_MINUTE
