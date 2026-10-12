from __future__ import annotations

"""Module 4: RAGAS Evaluation — 4 metrics + failure analysis."""

import os, sys, json
import math
from dataclasses import asdict, dataclass, is_dataclass
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (OPENAI_API_KEY, RAGAS_EMBEDDING_MODEL,
                    RAGAS_EVALUATOR_MODEL, TEST_SET_PATH)

METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


def _validated_score(value, metric: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"RAGAS metric {metric} must be a finite float in [0, 1].")
    try:
        score = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"RAGAS metric {metric} must be a finite float in [0, 1].") from None
    if not math.isfinite(score) or not 0 <= score <= 1:
        raise ValueError(f"RAGAS metric {metric} must be a finite float in [0, 1].")
    return score


def _contexts_or_fallback(value, fallback: list[str]) -> list[str]:
    """Normalize list-like dataframe cells without truth-testing NumPy arrays."""
    if value is None:
        return list(fallback)
    if isinstance(value, str):
        return [value] if value else list(fallback)
    try:
        contexts = list(value)
    except TypeError:
        return list(fallback)
    return [str(context) for context in contexts if context is not None]


def _result_value(result, name: str):
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)


@dataclass
class EvalResult:
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float


def load_test_set(path: str = TEST_SET_PATH) -> list[dict]:
    """Load test set from JSON. (Đã implement sẵn)"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def evaluate_ragas(questions: list[str], answers: list[str],
                   contexts: list[list[str]], ground_truths: list[str]) -> dict:
    """Run four RAGAS metrics with explicit, reportable evaluator models."""
    lengths = (len(questions), len(answers), len(contexts), len(ground_truths))
    if len(set(lengths)) != 1:
        raise ValueError("RAGAS input lists must have the same length.")
    if not questions:
        raise ValueError("RAGAS evaluation requires at least one question.")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not configured for RAGAS evaluation.")

    try:
        from datasets import Dataset
        from ragas import evaluate
        from ragas.embeddings import LangchainEmbeddingsWrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })
        evaluator_llm = ChatOpenAI(
            model=RAGAS_EVALUATOR_MODEL,
            temperature=0,
            api_key=OPENAI_API_KEY,
        )
        evaluator_embeddings = OpenAIEmbeddings(
            model=RAGAS_EMBEDDING_MODEL,
            api_key=OPENAI_API_KEY,
        )
        result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=LangchainLLMWrapper(evaluator_llm),
            embeddings=LangchainEmbeddingsWrapper(evaluator_embeddings),
        )
        frame = result.to_pandas()
        if len(frame) != len(questions):
            raise ValueError(
                f"RAGAS returned {len(frame)} rows for {len(questions)} input questions."
            )
        per_question = []
        for source_index, (_, row) in enumerate(frame.iterrows()):
            for field, source_values in (
                ("question", questions),
                ("answer", answers),
                ("ground_truth", ground_truths),
            ):
                if row.get(field) != source_values[source_index]:
                    raise ValueError(f"RAGAS returned rows out of order at {field}.")
            row_contexts = _contexts_or_fallback(row.get("contexts"), contexts[source_index])
            per_question.append(EvalResult(
                question=questions[source_index],
                answer=answers[source_index],
                contexts=row_contexts,
                ground_truth=ground_truths[source_index],
                faithfulness=_validated_score(row.get("faithfulness"), "faithfulness"),
                answer_relevancy=_validated_score(row.get("answer_relevancy"), "answer_relevancy"),
                context_precision=_validated_score(row.get("context_precision"), "context_precision"),
                context_recall=_validated_score(row.get("context_recall"), "context_recall"),
            ))

        if len(per_question) != len(questions):
            raise ValueError("RAGAS returned an incomplete per-question result.")
        aggregates = {name: sum(getattr(item, name) for item in per_question) / len(per_question)
                      for name in METRIC_NAMES}
        return {
            **aggregates,
            "per_question": per_question,
            "metadata": {"evaluator_models": sorted({
                RAGAS_EVALUATOR_MODEL,
                RAGAS_EMBEDDING_MODEL,
            })},
        }
    except Exception as exc:
        if isinstance(exc, (ValueError, RuntimeError)) and str(exc).startswith((
            "RAGAS returned", "RAGAS metric", "RAGAS evaluation requires", "OPENAI_API_KEY"
        )):
            raise
        raise RuntimeError(f"RAGAS evaluation failed ({type(exc).__name__}).") from exc


def failure_analysis(eval_results: list[EvalResult], bottom_n: int = 10) -> list[dict]:
    """Analyze bottom-N worst questions using Diagnostic Tree."""
    if bottom_n <= 0:
        return []
    diagnostic_tree = {
        "faithfulness": (
            "LLM generated claims not supported by the retrieved context",
            "Tighten the system prompt and lower answer temperature.",
        ),
        "answer_relevancy": (
            "The answer does not directly address the question",
            "Make the answer prompt require a direct response to the asked question.",
        ),
        "context_precision": (
            "Irrelevant context is ranked above useful evidence",
            "Improve hybrid retrieval and CrossEncoder reranking.",
        ),
        "context_recall": (
            "Retrieved context is missing evidence needed for the answer",
            "Improve chunk boundaries or add exact Vietnamese keywords to BM25.",
        ),
    }

    analyses = []
    for result in eval_results:
        scores = {name: _validated_score(_result_value(result, name), name) for name in METRIC_NAMES}
        worst_metric = min(METRIC_NAMES, key=scores.get)
        average_score = sum(scores.values()) / len(METRIC_NAMES)
        diagnosis, suggested_fix = diagnostic_tree[worst_metric]
        item = asdict(result) if is_dataclass(result) else dict(result)
        item.update({
            "average_score": average_score,
            "worst_metric": worst_metric,
            "score": scores[worst_metric],
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
        analyses.append(item)
    analyses.sort(key=lambda item: item["average_score"])
    return analyses[:bottom_n]


def save_report(results: dict, failures: list[dict], path: str = "reports/ragas_report.json"):
    """Save evaluation report to JSON. (Đã implement sẵn)"""
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    per_question = [
        asdict(item) if is_dataclass(item) else dict(item)
        for item in results.get("per_question", [])
    ]
    report = {
        "aggregate": {name: _validated_score(results.get(name), name) for name in METRIC_NAMES},
        "num_questions": len(per_question),
        "per_question": per_question,
        "failures": failures,
    }
    if results.get("evaluation_error"):
        report["evaluation_error"] = results["evaluation_error"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
    print(f"Report saved to {path}")


if __name__ == "__main__":
    test_set = load_test_set()
    print(f"Loaded {len(test_set)} test questions")
    print("Run pipeline.py first to generate answers, then call evaluate_ragas().")
