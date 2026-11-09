"""Judge LLM evaluation (LLM-as-a-judge, no reference answer needed), on JUDGE_OPENAI_MODEL.

Three metrics, each a 0-1 score, computed by one structured-output call each (run in parallel):

  faithfulness      : the answer is split into atomic claims; score = supported claims / all claims
  groundedness      : overall rating 0 (not grounded) / 1 (partially) / 2 (fully grounded) -> rating / 2
  context_precision : each retrieved context is judged useful or not for the answer; score = average precision
                      over the ranked contexts (useful chunks ranked first score higher)

The definitions follow the common RAG-evaluation metrics (faithfulness, response groundedness, context precision
without reference) without depending on an evaluation framework.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from functools import lru_cache

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from .config import get_settings


@dataclass
class JudgeResult:
    scores: dict[str, float]
    passed: bool
    failed: list[str] = field(default_factory=list)


# ---------------------------- structured outputs ----------------------------


class Claim(BaseModel):
    claim: str = Field(description="One atomic factual statement made by the answer")
    supported: bool = Field(description="True only if the claim can be directly inferred from the CONTEXT")


class FaithfulnessVerdict(BaseModel):
    claims: list[Claim] = Field(description="Every factual claim in the answer (skip citations, greetings, "
                                            "disclaimers and questions back to the user)")


class GroundednessVerdict(BaseModel):
    rating: int = Field(ge=0, le=2, description="0 = not grounded, 1 = partially grounded, 2 = fully grounded")
    reason: str = Field(description="One sentence")


class ContextVerdict(BaseModel):
    useful: list[bool] = Field(description="One entry per numbered context, in order: was it useful for "
                                           "arriving at the answer?")


FAITHFULNESS_PROMPT = """You verify whether an answer is faithful to the retrieved context.
1. Break the ANSWER into atomic factual claims.
2. For each claim, decide if it can be directly inferred from the CONTEXT (no outside knowledge).
Ignore citation markers such as [KB-NET-1001, p. 2] or [WEB-1], formatting and disclaimers: judge only the factual content.

QUESTION:
{question}

CONTEXT:
{context}

ANSWER:
{answer}"""

GROUNDEDNESS_PROMPT = """Rate how well the ANSWER is grounded in the CONTEXT.
2 = every statement is supported by the context; 1 = some statements are supported, others are not;
0 = the answer is not supported by the context.
Ignore citation markers such as [KB-NET-1001, p. 2] or [WEB-1], formatting and disclaimers: judge only the factual content.

CONTEXT:
{context}

ANSWER:
{answer}"""

PRECISION_PROMPT = """For each numbered CONTEXT, decide whether it was useful for arriving at the ANSWER to the
QUESTION. Return exactly {n} booleans, in the same order as the contexts.

QUESTION:
{question}

ANSWER:
{answer}

CONTEXTS:
{contexts}"""


@lru_cache(maxsize=1)
def _judge_llm() -> ChatOpenAI:
    s = get_settings()
    extra = {"reasoning_effort": s.judge_reasoning_effort} if s.judge_reasoning_effort else {}
    return ChatOpenAI(model=s.judge_model, max_retries=s.max_retries, **extra)


def _thresholds() -> dict[str, float]:
    s = get_settings()
    return {"faithfulness": s.faithfulness_threshold, "groundedness": s.groundedness_threshold,
            "context_precision": s.context_precision_threshold}


# ---------------------------- metrics ----------------------------


def faithfulness(question: str, answer: str, contexts: list[str]) -> float:
    verdict: FaithfulnessVerdict = _judge_llm().with_structured_output(FaithfulnessVerdict).invoke(
        FAITHFULNESS_PROMPT.format(question=question, context="\n\n".join(contexts), answer=answer))
    if not verdict.claims:  # nothing asserted -> nothing unfaithful
        return 1.0
    return sum(c.supported for c in verdict.claims) / len(verdict.claims)


def groundedness(answer: str, contexts: list[str]) -> float:
    verdict: GroundednessVerdict = _judge_llm().with_structured_output(GroundednessVerdict).invoke(
        GROUNDEDNESS_PROMPT.format(context="\n\n".join(contexts), answer=answer))
    return verdict.rating / 2


def average_precision(useful: list[bool]) -> float:
    """Mean of precision@k over the ranks k that hold a useful context (0 when none is useful)."""
    hits, total = 0, 0.0
    for k, ok in enumerate(useful, start=1):
        if ok:
            hits += 1
            total += hits / k
    return total / hits if hits else 0.0


def context_precision(question: str, answer: str, contexts: list[str]) -> float:
    if not contexts:
        return 0.0
    numbered = "\n\n".join(f"[{i}] {c}" for i, c in enumerate(contexts, start=1))
    verdict: ContextVerdict = _judge_llm().with_structured_output(ContextVerdict).invoke(
        PRECISION_PROMPT.format(question=question, answer=answer, contexts=numbered, n=len(contexts)))
    useful = (list(verdict.useful) + [False] * len(contexts))[: len(contexts)]  # tolerate a wrong length
    return average_precision(useful)


def evaluate(question: str, answer: str, contexts: list[str], timeout: float | None = None) -> JudgeResult:
    """Run the three metrics in parallel on the judge model and compare them with the .env thresholds."""
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="judge") as pool:
        futures = {
            "faithfulness": pool.submit(faithfulness, question, answer, contexts),
            "groundedness": pool.submit(groundedness, answer, contexts),
            "context_precision": pool.submit(context_precision, question, answer, contexts),
        }
        scores = {name: round(float(f.result(timeout=timeout)), 3) for name, f in futures.items()}
    failed = [m for m, threshold in _thresholds().items() if scores.get(m, 0.0) < threshold]
    return JudgeResult(scores=scores, passed=not failed, failed=failed)
