"""Student contracts; no RAGAS API calls."""
from types import SimpleNamespace
import sys
from unittest.mock import Mock

import pytest

from src.phase_a_ragas import (load_test_set_50q, group_by_distribution, run_ragas_50q,
                               bottom_10, cluster_analysis, RagasResult)

pytestmark = pytest.mark.student


@pytest.fixture
def dummy_results():
    return [RagasResult(i+1, dist, f"Q{i}", "A", ["C"], "GT", *scores)
            for i, (dist, scores) in enumerate([
                ("factual", (.9,.8,.7,.6)), ("multi_hop", (.3,.4,.5,.2)),
                ("adversarial", (.1,.2,.3,.4)), ("factual", (.8,.7,.9,.8)),
                ("multi_hop", (.2,.3,.1,.2))])]


def test_group_exact_counts():
    groups = group_by_distribution(load_test_set_50q())
    assert set(groups) == {"factual","multi_hop","adversarial"}
    assert [len(groups[d]) for d in ("factual","multi_hop","adversarial")] == [20,20,10]


def test_group_keeps_empty_keys_and_input_rows():
    rows = [{"id": 9, "distribution": "multi_hop"}]
    groups = group_by_distribution(rows)
    assert groups == {"factual": [], "multi_hop": rows, "adversarial": []}


def test_ragas_adapter_preserves_rows(monkeypatch):
    questions = load_test_set_50q()
    answers = [{**q, "answer": "A", "contexts": ["C"]} for q in questions]
    metrics = [SimpleNamespace(faithfulness=.8, answer_relevancy=.7,
                               context_precision=.6, context_recall=.5) for _ in answers]
    evaluator_models = ["evaluator-test", "embedding-test"]
    evaluate = Mock(return_value={"per_question": metrics,
                                  "metadata": {"evaluator_models": evaluator_models}})
    monkeypatch.setitem(sys.modules, "src.m4_eval", SimpleNamespace(evaluate_ragas=evaluate))
    evaluation = run_ragas_50q(answers)
    results = evaluation.results
    assert evaluation.evaluator_models == evaluator_models
    assert len(results) == 50
    assert [r.question_id for r in results] == [q["id"] for q in questions]
    assert results[0].faithfulness == .8
    evaluate.assert_called_once()
    assert list(evaluate.call_args.args[0]) == [q["question"] for q in questions]


def test_ragas_adapter_rejects_wrong_number_of_answers():
    with pytest.raises(ValueError, match="50"):
        run_ragas_50q(load_test_set_50q()[:-1])


def test_bottom_nonempty_sorted_complete(dummy_results):
    rows = bottom_10(dummy_results)
    assert len(rows) == 5
    assert [r["rank"] for r in rows] == [1,2,3,4,5]
    assert [r["avg_score"] for r in rows] == sorted(r["avg_score"] for r in rows)
    assert rows[0]["question_id"] == 5
    for row in rows:
        assert {"question_id","distribution","question","worst_metric",
                "diagnosis","suggested_fix"} <= row.keys()
        assert row["diagnosis"].strip() and row["suggested_fix"].strip()


def test_bottom_capped_at_ten(dummy_results):
    repeated = [RagasResult(i+1,r.distribution,r.question,r.answer,r.contexts,r.ground_truth,
                           r.faithfulness,r.answer_relevancy,r.context_precision,r.context_recall)
                for i,r in enumerate(dummy_results*4)]
    assert len(bottom_10(repeated)) == 10


def test_cluster_matrix(dummy_results):
    result = cluster_analysis(dummy_results)
    assert result["matrix"] == {
        "faithfulness":{"factual":0,"multi_hop":0,"adversarial":1},
        "answer_relevancy":{"factual":1,"multi_hop":0,"adversarial":0},
        "context_precision":{"factual":0,"multi_hop":1,"adversarial":0},
        "context_recall":{"factual":1,"multi_hop":1,"adversarial":0}}
    assert result["dominant_failure_metric"] == "context_recall"
    assert result["insight"].strip()


def test_weakest_distribution_is_quality_not_size():
    results = []
    for dist,count,value in [("factual",20,.95),("multi_hop",20,.70),("adversarial",10,.10)]:
        for _ in range(count):
            results.append(RagasResult(len(results)+1,dist,"Q","A",["C"],"GT",
                                       value,value,value,value))
    assert cluster_analysis(results)["dominant_failure_distribution"] == "adversarial"


def test_cluster_analysis_ignores_empty_distributions():
    row = RagasResult(1, "multi_hop", "Q", "A", ["C"], "GT", .5, .5, .5, .5)
    result = cluster_analysis([row])
    assert result["distribution_avg_scores"] == {"multi_hop": .5}
    assert result["dominant_failure_distribution"] == "multi_hop"


def test_cluster_analysis_empty_results_does_not_invent_a_weakest_group():
    result = cluster_analysis([])
    assert result["distribution_avg_scores"] == {}
    assert result["dominant_failure_distribution"] is None
    assert result["dominant_failure_metric"] is None
    assert result["insight"].strip()
