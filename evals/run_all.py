"""Upload gold datasets to Langfuse and run experiments against the pipeline.

Usage:  uv run python evals/run_all.py [--backend llm|decide] [relevance|classification|groundedness]

--backend decide runs the relevance and classification sets through the one
typed Jev call (classification/decide.py) instead of the LLM pair, as its own
experiment run, so the two backends sit side by side in Langfuse.

Requires LANGFUSE_* and OLLAMA_API_KEY in the environment (.env is read by
common.config; export them for the Langfuse SDK too). Results appear in the
Langfuse UI under Datasets → <name> → Runs.
"""

import json
import sys
from pathlib import Path

from langfuse import Evaluation, get_client
from pydantic import BaseModel, Field

from classification.decide import QUESTIONS, state_for, to_results
from classification.schemas import ClassificationResult, GateResult
from common.config import get_settings
from common.decisions import decide
from common.llm import structured_chat
from common.observability import fetch_prompt
from common.taxonomy import prompt_menu, valid_subsector
from correlation.schemas import ThreadLinkResult

DATASET_DIR = Path(__file__).parent / "datasets"
BACKEND = "llm"  # or "decide" — set from argv in __main__

get_settings()  # bridges .env Langfuse keys into process env for the SDK
langfuse = get_client()


def upload(name: str, filename: str) -> None:
    langfuse.create_dataset(name=name)
    items = [json.loads(line) for line in (DATASET_DIR / filename).read_text().splitlines() if line.strip()]
    for item in items:
        langfuse.create_dataset_item(
            dataset_name=name,
            input=item["input"],
            expected_output=item["expected_output"],
        )
    print(f"uploaded {len(items)} items to dataset '{name}'")


# ── Relevance gate ───────────────────────────────────────────────────


async def _decide_item(item, trace_name: str):
    d = await decide(state_for(item.input["title"], item.input["body"]), QUESTIONS, trace_name=trace_name)
    return to_results(d, source_country=None)


async def relevance_task(*, item, **kwargs):
    if BACKEND == "decide":
        gate, _ = await _decide_item(item, "eval-relevance-decide")
        return gate.model_dump()
    prompt = fetch_prompt("relevance-gate")
    messages = prompt.compile(title=item.input["title"], body=item.input["body"])
    result = await structured_chat(
        model=get_settings().prism_model_gate,
        messages=messages,
        output_model=GateResult,
        trace_name="eval-relevance-gate",
    )
    return result.model_dump()


def relevance_evaluator(*, input, output, expected_output, **kwargs):
    correct = bool(output and output.get("is_relevant") == expected_output["is_relevant"])
    return Evaluation(name="relevance_accuracy", value=1.0 if correct else 0.0)


# ── Classifier ───────────────────────────────────────────────────────


async def classification_task(*, item, **kwargs):
    if BACKEND == "decide":
        _, cls = await _decide_item(item, "eval-classifier-decide")
        return cls.model_dump() if cls else None
    prompt = fetch_prompt("classifier")
    messages = prompt.compile(
        title=item.input["title"], body=item.input["body"], taxonomy=prompt_menu()
    )
    result = await structured_chat(
        model=get_settings().prism_model_classify,
        messages=messages,
        output_model=ClassificationResult,
        trace_name="eval-classifier",
    )
    result.subsector = valid_subsector(result.sector, result.subsector)
    return result.model_dump()


def sector_evaluator(*, input, output, expected_output, **kwargs):
    correct = bool(output and output.get("sector") == expected_output["sector"])
    return Evaluation(name="sector_accuracy", value=1.0 if correct else 0.0)


def subsector_evaluator(*, input, output, expected_output, **kwargs):
    expected = expected_output.get("subsector")
    if expected is None:
        return None  # unlabeled item — don't count either way
    correct = bool(output and output.get("subsector") == expected)
    return Evaluation(name="subsector_accuracy", value=1.0 if correct else 0.0)


def role_evaluator(*, input, output, expected_output, **kwargs):
    correct = bool(
        output is not None
        and set(output.get("role_interests", [])) == set(expected_output["role_interests"])
    )
    return Evaluation(name="role_interest_accuracy", value=1.0 if correct else 0.0)


# ── Agent groundedness (LLM-as-judge) ────────────────────────────────


class JudgeVerdict(BaseModel):
    grounded: float = Field(ge=0.0, le=1.0)
    citation_quality: float = Field(ge=0.0, le=1.0)
    correct_refusal: bool | None = None
    reasoning: str


async def groundedness_task(*, item, **kwargs):
    """Run the agent-qa prompt over the gold sources (no DB needed)."""
    from common.llm import plain_chat

    prompt = fetch_prompt("agent-qa")
    messages = prompt.compile(
        event_title="(eval)",
        structured="{}",
        sources=item.input["sources"],
        question=item.input["question"],
    )
    return await plain_chat(
        model=get_settings().prism_model_agent,
        messages=messages,
        trace_name="eval-agent-qa",
    )


async def judge_evaluator(*, input, output, expected_output, **kwargs):
    prompt = fetch_prompt("judge-groundedness")
    messages = prompt.compile(
        sources=input["sources"], question=input["question"], answer=output or ""
    )
    verdict = await structured_chat(
        model=get_settings().prism_model_judge,
        messages=messages,
        output_model=JudgeVerdict,
        trace_name="judge-groundedness",
    )
    evals = [
        Evaluation(name="grounded", value=verdict.grounded, comment=verdict.reasoning),
        Evaluation(name="citation_quality", value=verdict.citation_quality),
    ]
    should_refuse = kwargs.get("expected_output", expected_output).get("should_refuse")
    if should_refuse is not None and verdict.correct_refusal is not None:
        evals.append(Evaluation(name="correct_refusal", value=1.0 if verdict.correct_refusal else 0.0))
    return evals


# ── Thread linking ───────────────────────────────────────────────────


async def thread_task(*, item, **kwargs):
    prompt = fetch_prompt("thread-link")
    messages = prompt.compile(**item.input)
    result = await structured_chat(
        model=get_settings().prism_model_correlate,
        messages=messages,
        output_model=ThreadLinkResult,
        trace_name="eval-thread-link",
    )
    return result.model_dump()


def thread_related_evaluator(*, input, output, expected_output, **kwargs):
    judgements = (output or {}).get("judgements") or []
    j = next((x for x in judgements if x.get("index") == 0), None)
    correct = bool(j is not None and bool(j.get("related")) == expected_output["related"])
    return Evaluation(name="thread_related_accuracy", value=1.0 if correct else 0.0)


def thread_direction_evaluator(*, input, output, expected_output, **kwargs):
    if not expected_output["related"]:
        return None  # direction only meaningful on related pairs
    judgements = (output or {}).get("judgements") or []
    j = next((x for x in judgements if x.get("index") == 0), None)
    correct = bool(j and j.get("related") and j.get("direction") == expected_output["direction"])
    return Evaluation(name="thread_direction_accuracy", value=1.0 if correct else 0.0)


# ── Story veto (grounded same-story judgment) ────────────────────────


async def veto_task(*, item, **kwargs):
    from correlation.partition import _StoryVeto

    prompt = fetch_prompt("story-veto")
    result = await structured_chat(
        model=get_settings().prism_model_gate,
        messages=prompt.compile(grounding=item.input["grounding"], candidate=item.input["candidate"]),
        output_model=_StoryVeto,
        trace_name="eval-story-veto",
        langfuse_prompt=prompt,
    )
    return result.model_dump()


def veto_evaluator(*, input, output, expected_output, **kwargs):
    correct = bool(output and output.get("same_story") == expected_output["same_story"])
    return Evaluation(name="veto_accuracy", value=1.0 if correct else 0.0)


def veto_keep_evaluator(*, input, output, expected_output, **kwargs):
    """Keep-precision: only scores the genuine developments (expected same_story=true)."""
    if not expected_output["same_story"]:
        return None
    return Evaluation(name="veto_keep_precision", value=1.0 if output and output.get("same_story") else 0.0)


def veto_separate_evaluator(*, input, output, expected_output, **kwargs):
    """Separation: only scores the contaminants (expected same_story=false)."""
    if expected_output["same_story"]:
        return None
    return Evaluation(name="veto_separation", value=1.0 if output and not output.get("same_story") else 0.0)


# ── Runner ───────────────────────────────────────────────────────────


def run_relevance():
    upload("prism-relevance", "relevance.jsonl")
    dataset = langfuse.get_dataset("prism-relevance")
    result = dataset.run_experiment(
        name=f"relevance-gate-{BACKEND}" if BACKEND != "llm" else "relevance-gate",
        description="Binary relevance gate accuracy",
        task=relevance_task,
        evaluators=[relevance_evaluator],
    )
    print(result.format())


def run_classification():
    upload("prism-classification", "classification.jsonl")
    dataset = langfuse.get_dataset("prism-classification")
    result = dataset.run_experiment(
        name=f"classifier-{BACKEND}" if BACKEND != "llm" else "classifier",
        description="Sector / role-interest / routing accuracy",
        task=classification_task,
        evaluators=[sector_evaluator, subsector_evaluator, role_evaluator],
    )
    print(result.format())


def run_threads():
    upload("prism-event-links", "event_links.jsonl")
    dataset = langfuse.get_dataset("prism-event-links")
    result = dataset.run_experiment(
        name="thread-link",
        description="Cross-event thread linking: related + direction accuracy",
        task=thread_task,
        evaluators=[thread_related_evaluator, thread_direction_evaluator],
    )
    print(result.format())


def run_groundedness():
    upload("prism-agent-groundedness", "agent_groundedness.jsonl")
    dataset = langfuse.get_dataset("prism-agent-groundedness")
    result = dataset.run_experiment(
        name="agent-groundedness",
        description="Agent answers judged for groundedness, citations, refusal",
        task=groundedness_task,
        evaluators=[judge_evaluator],
    )
    print(result.format())


def run_veto():
    upload("prism-story-veto", "story_veto.jsonl")
    dataset = langfuse.get_dataset("prism-story-veto")
    result = dataset.run_experiment(
        name="story-veto",
        description="Grounded veto: keep genuine developments, separate contaminants",
        task=veto_task,
        evaluators=[veto_evaluator, veto_keep_evaluator, veto_separate_evaluator],
    )
    print(result.format())


RUNS = {
    "relevance": run_relevance,
    "classification": run_classification,
    "threads": run_threads,
    "groundedness": run_groundedness,
    "veto": run_veto,
}


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--backend" in args:
        i = args.index("--backend")
        BACKEND = args[i + 1]
        del args[i : i + 2]
    targets = args or list(RUNS)
    for target in targets:
        print(f"\n=== {target} ===")
        RUNS[target]()
    langfuse.flush()
