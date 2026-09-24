"""web/scripts/retry-next-font.sh: builds are retried when next/font's Google
Fonts fetch failed — four builds on 2026-09-23, one a production deploy — and
never for anything else, so a real build error still fails at once."""

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "web" / "scripts" / "retry-next-font.sh"
FONT_ERROR = "An error occurred in `next/font`.\nTypeError: Cannot read properties of null (reading '1')"


def _fake_build(tmp_path: Path, outcomes: list[tuple[int, str]]) -> tuple[Path, Path]:
    """A 'build' that answers with the next outcome each time it is run."""
    runs = tmp_path / "runs"
    runs.write_text("0")
    script = tmp_path / "build.sh"
    # Each answer from a file: the real message has backticks, which bash
    # would run as a command inside a double-quoted string.
    for i, (_, out) in enumerate(outcomes):
        (tmp_path / f"out{i}").write_text(out)
    cases = "\n".join(f"  {i}) cat {tmp_path / f'out{i}'}; exit {code};;" for i, (code, _) in enumerate(outcomes))
    script.write_text(f"""#!/usr/bin/env bash
n=$(cat {runs}); echo $((n + 1)) > {runs}
case $n in
{cases}
esac
""")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script, runs


def _run(script: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "NEXT_FONT_WAIT_S": "0"}
    return subprocess.run([str(SCRIPT), str(script)], capture_output=True, text=True, env=env, timeout=30)


def test_a_font_fetch_failure_is_tried_again(tmp_path):
    build, runs = _fake_build(tmp_path, [(1, FONT_ERROR), (1, FONT_ERROR), (0, "Compiled")])
    assert _run(build).returncode == 0
    assert runs.read_text().strip() == "3"


def test_any_other_failure_fails_at_once(tmp_path):
    build, runs = _fake_build(tmp_path, [(2, "Type error: x is not assignable"), (0, "Compiled")])
    assert _run(build).returncode == 2
    assert runs.read_text().strip() == "1"


def test_it_gives_up_after_three_tries(tmp_path):
    build, runs = _fake_build(tmp_path, [(1, FONT_ERROR)] * 5)
    result = _run(build)
    assert result.returncode == 1 and runs.read_text().strip() == "3"
    assert "retrying" in result.stdout
