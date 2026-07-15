"""Upload gold datasets to Langfuse and run experiments against the pipeline.

Usage:  uv run python evals/run_all.py [relevance|classification|groundedness]

Requires LANGFUSE_* and OLLAMA_API_KEY in the environment (.env is read by
common.config; export them for the Langfuse SDK too). Results appear in the
Langfuse UI under Datasets → <name> → Runs.
"""

import json
import sys
from pathlib import Path

from langfuse import Evaluation, get_client
from pydantic import BaseModel, Field

from classification.schemas import ClassificationResult, GateResult
from common.config import get_settings
from common.llm import structured_chat
from common.observability import fetch_prompt

DATASET_DIR = Path(__file__).parent / "datasets"

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


async def relevance_task(*, item, **kwargs):
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
    prompt = fetch_prompt("classifier")
    messages = prompt.compile(title=item.input["title"], body=item.input["body"])
    result = await structured_chat(
        model=get_settings().prism_model_classify,
        messages=messages,
        output_model=ClassificationResult,
        trace_name="eval-classifier",
    )
    return result.model_dump()


def sector_evaluator(*, input, output, expected_output, **kwargs):
    correct = bool(output and output.get("sector") == expected_output["sector"])
    return Evaluation(name="sector_accuracy", value=1.0 if correct else 0.0)


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


# ── Runner ───────────────────────────────────────────────────────────


def run_relevance():
    upload("prism-relevance", "relevance.jsonl")
    dataset = langfuse.get_dataset("prism-relevance")
    result = dataset.run_experiment(
        name="relevance-gate",
        description="Binary relevance gate accuracy",
        task=relevance_task,
        evaluators=[relevance_evaluator],
    )
    print(result.format())


def run_classification():
    upload("prism-classification", "classification.jsonl")
    dataset = langfuse.get_dataset("prism-classification")
    result = dataset.run_experiment(
        name="classifier",
        description="Sector / role-interest / routing accuracy",
        task=classification_task,
        evaluators=[sector_evaluator, role_evaluator],
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


RUNS = {
    "relevance": run_relevance,
    "classification": run_classification,
    "groundedness": run_groundedness,
}


if __name__ == "__main__":
    targets = sys.argv[1:] or list(RUNS)
    for target in targets:
        print(f"\n=== {target} ===")
        RUNS[target]()
    langfuse.flush()
