from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

import config
from src import m4_eval


def score_rows(questions, *, faithfulness=0.8):
    return pd.DataFrame([
        {
            "question": question,
            "answer": f"answer-{index}",
            "contexts": [f"context-{index}"],
            "ground_truth": f"reference-{index}",
            "faithfulness": faithfulness,
            "answer_relevancy": 0.7,
            "context_precision": 0.6,
            "context_recall": 0.5,
        }
        for index, question in enumerate(questions)
    ])


def test_evaluate_ragas_returns_ordered_rows_and_used_model_ids(monkeypatch):
    import ragas

    monkeypatch.setattr(m4_eval, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ragas, "evaluate", lambda dataset, **kwargs: SimpleNamespace(
        to_pandas=lambda: score_rows(dataset["question"])
    ))
    questions = ["first question", "second question"]
    answers = ["answer-0", "answer-1"]
    contexts = [["context-0"], ["context-1"]]
    references = ["reference-0", "reference-1"]

    result = m4_eval.evaluate_ragas(questions, answers, contexts, references)

    assert [row.question for row in result["per_question"]] == questions
    assert [row.answer for row in result["per_question"]] == answers
    assert result["metadata"]["evaluator_models"] == sorted(
        ["gpt-4o-mini-2024-07-18", "text-embedding-3-small"]
    )
    assert config.RAGAS_EVALUATOR_MODEL == "gpt-4o-mini-2024-07-18"
    assert config.RAGAS_EMBEDDING_MODEL == "text-embedding-3-small"
    assert result["faithfulness"] == pytest.approx(0.8)


def test_evaluate_ragas_rejects_misaligned_inputs():
    with pytest.raises(ValueError, match="same length"):
        m4_eval.evaluate_ragas(["q"], ["a"], [], ["ref"])


@pytest.mark.parametrize("bad_score", [float("nan"), float("inf"), -0.1, 1.1])
def test_evaluate_ragas_rejects_invalid_metric_instead_of_zeroing(monkeypatch, bad_score):
    import ragas

    monkeypatch.setattr(m4_eval, "OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ragas, "evaluate", lambda dataset, **kwargs: SimpleNamespace(
        to_pandas=lambda: score_rows(dataset["question"], faithfulness=bad_score)
    ))

    with pytest.raises(ValueError, match="faithfulness"):
        m4_eval.evaluate_ragas(
            ["q"], ["answer-0"], [["context"]], ["reference-0"]
        )


def test_evaluate_ragas_propagates_evaluation_failure(monkeypatch):
    import ragas

    monkeypatch.setattr(m4_eval, "OPENAI_API_KEY", "test-key")

    def fail(*args, **kwargs):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ragas, "evaluate", fail)
    with pytest.raises(RuntimeError, match="RAGAS evaluation failed"):
        m4_eval.evaluate_ragas(["q"], ["a"], [["context"]], ["ref"])


def test_legacy_failure_report_helpers_do_not_fill_missing_scores_with_zero(tmp_path):
    with pytest.raises(ValueError, match="faithfulness"):
        m4_eval.failure_analysis([{}])
    with pytest.raises(ValueError, match="faithfulness"):
        m4_eval.save_report({}, [], str(tmp_path / "report.json"))
