"""`.env.example` is the only map of the configuration surface. Keep it honest.

It had drifted three ways at once: 10 of 39 Settings fields missing, model IDs
naming a model the code no longer defaults to, and every `os.environ`-only
variable absent — the last being the worst, because those never appear in the
Settings class either, so nothing in the repo documented them.

Nobody notices a stale example file; you only find out when a deploy is missing
a variable nobody knew existed.
"""

import re
from pathlib import Path

from common.config import Settings

ENV_EXAMPLE = Path(__file__).resolve().parent.parent / ".env.example"


def _declared() -> set[str]:
    """Keys in .env.example, including ones commented out as documentation."""
    text = ENV_EXAMPLE.read_text()
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]*)=", text, re.M))


def test_every_settings_field_is_documented():
    missing = sorted(f.upper() for f in Settings.model_fields if f.upper() not in _declared())
    assert not missing, (
        f".env.example is missing {len(missing)} setting(s): {missing}. "
        "A config field nobody can discover is a deploy waiting to fail."
    )


def test_the_runtime_only_variables_are_documented():
    """These are read via os.environ and never appear in Settings, so this file
    is the ONLY place they are written down."""
    for var in (
        "PRISM_SERVICE_ROLE", "PRISM_STAGES", "PRISM_PARTITION_INTERVAL_S",
        "PRISM_REQUIRE_DB", "LOG_LEVEL", "PORT",
    ):
        assert var in _declared(), f"{var} is read from os.environ but undocumented"


def test_tracing_is_documented_as_off():
    """The cost switch. If the example ships it enabled, someone copies it and
    starts paying to observe a pipeline they haven't run yet."""
    text = ENV_EXAMPLE.read_text()
    assert re.search(r"^PRISM_LANGFUSE_ENABLED=false", text, re.M)
