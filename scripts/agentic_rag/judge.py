"""Judge LLM evaluation with RAGAS: faithfulness, response groundedness, context precision (no reference needed)."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

from openai import AsyncOpenAI
from ragas.llms import llm_factory
from ragas.metrics.collections import ContextPrecisionWithoutReference, Faithfulness, ResponseGroundedness

from .config import get_settings


@dataclass
class JudgeResult:
    scores: dict[str, float]
    passed: bool
    failed: list[str] = field(default_factory=list)


def _thresholds() -> dict[str, float]:
    s = get_settings()
    return {"faithfulness": s.faithfulness_threshold, "groundedness": s.groundedness_threshold,
            "context_precision": s.context_precision_threshold}


def _judge_llm(client: AsyncOpenAI):
    llm = llm_factory(get_settings().judge_model, client=client)
    # Workaround: RAGAS detects reasoning models by parsing "gpt-<int>" and misses names like "gpt-6.1-sol",
    # so it would send `max_tokens` (rejected). Use the reasoning-model parameters explicitly; reasoning tokens
    # count against the limit, so it must be generous; low effort keeps the judge fast.
    llm.model_args.pop("max_tokens", None)
    llm.model_args.pop("top_p", None)
    llm.model_args.update(max_completion_tokens=16000, temperature=1.0, reasoning_effort="low")
    return llm


async def _score(question: str, answer: str, contexts: list[str]) -> dict[str, float]:
    # The client is created AND closed inside this event loop. Otherwise its HTTP connection pool is
    # garbage-collected after asyncio.run() has closed the loop -> "RuntimeError: Event loop is closed".
    async with AsyncOpenAI() as client:
        llm = _judge_llm(client)
        faithfulness, groundedness, precision = await asyncio.gather(
            Faithfulness(llm=llm).ascore(user_input=question, response=answer, retrieved_contexts=contexts),
            ResponseGroundedness(llm=llm).ascore(response=answer, retrieved_contexts=contexts),
            ContextPrecisionWithoutReference(llm=llm).ascore(user_input=question, response=answer,
                                                             retrieved_contexts=contexts),
        )
    return {"faithfulness": round(float(faithfulness.value), 3), "groundedness": round(float(groundedness.value), 3),
            "context_precision": round(float(precision.value), 3)}


def evaluate(question: str, answer: str, contexts: list[str], timeout: float | None = None) -> JudgeResult:
    """Run the three RAGAS metrics in parallel on the judge model and compare with the .env thresholds.

    RAGAS is async; it runs in a worker thread with its own event loop so this also works inside Jupyter.
    """
    get_settings()  # ensures .env (OPENAI_API_KEY) is loaded before the async client is created
    with ThreadPoolExecutor(max_workers=1) as pool:
        scores = pool.submit(asyncio.run, _score(question, answer, contexts)).result(timeout=timeout)
    failed = [m for m, threshold in _thresholds().items() if scores.get(m, 0.0) < threshold]
    return JudgeResult(scores=scores, passed=not failed, failed=failed)
