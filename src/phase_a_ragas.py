from __future__ import annotations

"""Phase A: RAGAS Production Evaluation — 50q, 3 distributions, cluster analysis."""

import json
import math
import os
import sys
from dataclasses import asdict, dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TEST_SET_PATH, ANSWERS_PATH, ARTIFACTS_DIR
from src.experiment_support import write_json

Distribution = str  # "factual" | "multi_hop" | "adversarial"

DIAGNOSTIC_TREE = {
    "faithfulness":      ("LLM hallucinating", "Tighten system prompt, lower temperature"),
    "context_recall":    ("Missing relevant chunks", "Improve chunking or add BM25"),
    "context_precision": ("Too many irrelevant chunks", "Add reranking or metadata filter"),
    "answer_relevancy":  ("Answer doesn't match question", "Improve prompt template"),
}


@dataclass
class RagasResult:
    question_id: int
    distribution: Distribution
    question: str
    answer: str
    contexts: list[str]
    ground_truth: str
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float

    @property
    def avg_score(self) -> float:
        return (self.faithfulness + self.answer_relevancy +
                self.context_precision + self.context_recall) / 4

    @property
    def worst_metric(self) -> str:
        scores = {
            "faithfulness":      self.faithfulness,
            "answer_relevancy":  self.answer_relevancy,
            "context_precision": self.context_precision,
            "context_recall":    self.context_recall,
        }
        return min(scores, key=scores.get)


# ─── Đã implement sẵn ────────────────────────────────────────────────────────

@dataclass
class RagasEvaluation:
    """Task 2 output: measured rows plus model identifiers reported by m4."""
    results: list[RagasResult]
    evaluator_models: list[str]

def load_test_set_50q(path: str = TEST_SET_PATH) -> list[dict]:
    """Load 50q test set với 3 distributions."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_answers(path: str = ANSWERS_PATH) -> list[dict]:
    """Load pre-generated answers từ setup_answers.py."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"answers_50q.json không tìm thấy tại {path}\n"
            "→ Chạy trước: python scripts/setup_answers.py --live"
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict]) -> dict:
    """Provided exporter: preserve the student-produced Task 3 rows verbatim."""
    per_dist: dict[str, dict] = {}
    for dist in ["factual", "multi_hop", "adversarial"]:
        subset = [r for r in results if r.distribution == dist]
        if subset:
            per_dist[dist] = {
                "count": len(subset),
                "faithfulness":      sum(r.faithfulness for r in subset) / len(subset),
                "answer_relevancy":  sum(r.answer_relevancy for r in subset) / len(subset),
                "context_precision": sum(r.context_precision for r in subset) / len(subset),
                "context_recall":    sum(r.context_recall for r in subset) / len(subset),
                "avg_score":         sum(r.avg_score for r in subset) / len(subset),
            }

    report = {
        "total_questions": len(results),
        "per_question": [asdict(r) for r in results],
        "per_distribution": per_dist,
        "failure_clusters": clusters,
        "bottom_10": bottom,
    }
    return report


def save_phase_a_report(results: list[RagasResult], clusters: dict, bottom: list[dict],
                        path: str = os.path.join(ARTIFACTS_DIR, "ragas_50q.json")) -> None:
    write_json(path, build_phase_a_report(results, clusters, bottom))



# ─── Tasks 1-4: Sinh viên implement ──────────────────────────────────────────

def group_by_distribution(test_set: list[dict]) -> dict[str, list[dict]]:
    """Task 1: Nhóm 50 câu hỏi theo 3 distributions.

    Returns:
        {"factual": [...], "multi_hop": [...], "adversarial": [...]}
    """
    groups = {"factual": [], "multi_hop": [], "adversarial": []}
    for item in test_set:
        distribution = item.get("distribution")
        if distribution not in groups:
            raise ValueError(f"Unknown or missing distribution: {distribution!r}.")
        groups[distribution].append(item)
    return groups


def run_ragas_50q(answers: list[dict]) -> RagasEvaluation:
    """Task 2: Chạy RAGAS 4 metrics trên toàn bộ 50 câu hỏi.

    Gợi ý — import từ Day 18 của bạn:
        from src.m4_eval import evaluate_ragas

    Steps:
        1. Extract questions, answers, contexts, ground_truths từ answers list
        2. Gọi evaluate_ragas() từ m4_eval.py
        3. Kết hợp kết quả với distribution info từ answers list
        4. Return RagasEvaluation(results, raw["metadata"]["evaluator_models"])
           m4 must report its actual LLM/embedding models; never guess JUDGE_MODEL.
    """
    if len(answers) != 50:
        raise ValueError(f"Phase A requires exactly 50 answers; received {len(answers)}.")
    try:
        from src.m4_eval import evaluate_ragas
    except ImportError as exc:
        raise RuntimeError("Missing m4 evaluator; cannot report its actual models.") from exc

    questions = [item["question"] for item in answers]
    answer_texts = [item["answer"] for item in answers]
    contexts = [item["contexts"] for item in answers]
    ground_truths = [item["ground_truth"] for item in answers]
    raw = evaluate_ragas(questions, answer_texts, contexts, ground_truths)
    if not isinstance(raw, dict):
        raise ValueError("m4 evaluator must return a dictionary.")

    per_question = raw.get("per_question")
    metadata = raw.get("metadata")
    evaluator_models = metadata.get("evaluator_models") if isinstance(metadata, dict) else None
    if not isinstance(per_question, list) or len(per_question) != len(answers):
        raise ValueError("m4 evaluator must return exactly 50 per-question metric rows.")
    if (not isinstance(evaluator_models, list) or not evaluator_models
            or any(not isinstance(model, str) or not model.strip() for model in evaluator_models)):
        raise ValueError("m4 evaluator must report non-empty evaluator_models metadata.")

    results = []
    for answer, metrics in zip(answers, per_question):
        def metric_value(name):
            value = metrics.get(name) if isinstance(metrics, dict) else getattr(metrics, name, None)
            if isinstance(value, bool):
                raise ValueError(f"Invalid RAGAS metric {name} for question {answer['id']}.")
            try:
                number = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"Invalid RAGAS metric {name} for question {answer['id']}.") from None
            if not math.isfinite(number) or not 0 <= number <= 1:
                raise ValueError(f"Invalid RAGAS metric {name} for question {answer['id']}.")
            return number

        results.append(RagasResult(
            question_id=answer["id"],
            distribution=answer["distribution"],
            question=answer["question"],
            answer=answer["answer"],
            contexts=answer["contexts"],
            ground_truth=answer["ground_truth"],
            faithfulness=metric_value("faithfulness"),
            answer_relevancy=metric_value("answer_relevancy"),
            context_precision=metric_value("context_precision"),
            context_recall=metric_value("context_recall"),
        ))
    return RagasEvaluation(results, list(evaluator_models))


def bottom_10(results: list[RagasResult]) -> list[dict]:
    """Task 3: Lấy 10 câu hỏi có avg_score thấp nhất.

    Returns:
        [{"rank": 1, "question_id": ..., "distribution": ...,
          "question": ..., "avg_score": ..., "worst_metric": ...,
          "diagnosis": ..., "suggested_fix": ...}, ...]
    """
    output = []
    for rank, result in enumerate(sorted(results, key=lambda row: row.avg_score)[:10], 1):
        diagnosis, suggested_fix = DIAGNOSTIC_TREE[result.worst_metric]
        output.append({
            "rank": rank,
            "question_id": result.question_id,
            "distribution": result.distribution,
            "question": result.question,
            "avg_score": round(result.avg_score, 4),
            "worst_metric": result.worst_metric,
            "diagnosis": diagnosis,
            "suggested_fix": suggested_fix,
        })
    return output


def cluster_analysis(results: list[RagasResult]) -> dict:
    """Task 4: Phân tích failure clusters theo (worst_metric × distribution).

    Matrix thống kê worst_metric của mọi câu, không coi mọi câu là một failure.
    Nhóm yếu nhất = distribution có avg_score trung bình thấp nhất (bỏ nhóm rỗng).
    Tổng matrix theo cột chỉ là kích thước nhóm 20/20/10, không đo chất lượng.

    Returns:
        {
          "matrix": {
            "faithfulness":      {"factual": 3, "multi_hop": 5, "adversarial": 2},
            "answer_relevancy":  {...},
            "context_precision": {...},
            "context_recall":    {...},
          },
          "dominant_failure_distribution": "multi_hop",
          "dominant_failure_metric": "context_recall",
          "insight": "..."
        }
    """
    distributions = ("factual", "multi_hop", "adversarial")
    metrics = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
    matrix = {
        metric: {distribution: 0 for distribution in distributions}
        for metric in metrics
    }
    totals = {distribution: 0.0 for distribution in distributions}
    counts = {distribution: 0 for distribution in distributions}
    for result in results:
        if result.distribution not in counts:
            raise ValueError(f"Unknown distribution: {result.distribution!r}.")
        if result.worst_metric not in matrix:
            raise ValueError(f"Unknown worst metric: {result.worst_metric!r}.")
        matrix[result.worst_metric][result.distribution] += 1
        totals[result.distribution] += result.avg_score
        counts[result.distribution] += 1

    means = {distribution: totals[distribution] / counts[distribution]
             for distribution in distributions if counts[distribution]}
    if not means:
        return {
            "matrix": matrix,
            "distribution_avg_scores": {},
            "dominant_failure_distribution": None,
            "dominant_failure_metric": None,
            "insight": "No RAGAS rows are available for cluster analysis.",
        }

    dominant_distribution = min(means, key=means.get)
    metric_counts = {metric: sum(matrix[metric].values()) for metric in metrics}
    dominant_metric = max(metric_counts, key=metric_counts.get)
    insight = (
        f"Distribution '{dominant_distribution}' has the lowest mean avg_score "
        f"({means[dominant_distribution]:.4f}). Metric '{dominant_metric}' is the "
        f"most frequent per-question worst metric ({metric_counts[dominant_metric]} rows). "
        f"Suggested direction: {DIAGNOSTIC_TREE[dominant_metric][1]}"
    )
    return {
        "matrix": matrix,
        "distribution_avg_scores": means,
        "dominant_failure_distribution": dominant_distribution,
        "dominant_failure_metric": dominant_metric,
        "insight": insight,
    }


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "a", *sys.argv[1:]]))
