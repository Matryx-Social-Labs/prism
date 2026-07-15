"""Publish the in-repo fallback prompts to Langfuse with the `production` label.

Run once after standing up Langfuse (and re-run to push updated fallbacks as
new versions):  uv run python evals/sync_prompts.py
"""

import json
from pathlib import Path

from langfuse import get_client

from common.config import get_settings

get_settings()  # bridges .env Langfuse keys into process env for the SDK

FALLBACK_DIR = Path(__file__).parent.parent / "common" / "prompts" / "fallbacks"

PROMPTS = [
    "relevance-gate",
    "classifier",
    "extract-shared",
    "perspective-impact",
    "thread-link",
    "lens-brief",
    "agent-qa",
    "judge-groundedness",
]


def main() -> None:
    langfuse = get_client()
    for name in PROMPTS:
        path = FALLBACK_DIR / f"{name}.json"
        messages = json.loads(path.read_text())
        langfuse.create_prompt(
            name=name,
            type="chat",
            prompt=messages,
            labels=["production"],
        )
        print(f"published {name} (labeled production)")
    langfuse.flush()


if __name__ == "__main__":
    main()
