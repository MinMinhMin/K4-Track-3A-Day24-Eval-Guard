"""Student logic uses mock SDK; never invokes the live judge."""
import json
from unittest.mock import Mock

import pytest

from src import phase_b_judge as phase

pytestmark = pytest.mark.student
Q,A,B,REF = "Q", "Correct detailed answer", "Wrong", "Policy reference"


def test_pairwise_uses_json_judge(openai_client):
    result = phase.pairwise_judge(Q,A,B,reference=REF)
    assert result == {"winner":"A","reasoning":"Matches the supplied policy.","scores":{"A":.9,"B":.2}}
    openai_client.chat.completions.create.assert_called_once()
    call = openai_client.chat.completions.create.call_args.kwargs
    assert REF in str(call["messages"])
    assert call["response_format"] == {"type":"json_object"}


@pytest.mark.parametrize("payload", [
    "not json",
    {"winner":"C","reasoning":"bad winner","scores":{"A":.9,"B":.2}},
    {"winner":"A","reasoning":" ","scores":{"A":.9,"B":.2}},
    {"winner":"A","reasoning":"ok","scores":{"A":True,"B":.2}},
    {"winner":"A","reasoning":"ok","scores":{"A":1.1,"B":.2}},
    {"winner":"tie","reasoning":"ok","scores":{"A":.9}},
])
def test_pairwise_rejects_malformed_or_invalid_result(openai_client, payload):
    content = payload if isinstance(payload, str) else json.dumps(payload)
    openai_client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content=content))])
    with pytest.raises((ValueError, TypeError, json.JSONDecodeError)):
        phase.pairwise_judge(Q,A,B,reference=REF)


@pytest.mark.parametrize("second_raw,expected,consistent", [("B","A",True),("A","tie",False)])
def test_swap_conversion_and_calls(monkeypatch,second_raw,expected,consistent):
    mocked = Mock(side_effect=[
        {"winner":"A","reasoning":"first","scores":{"A":.9,"B":.2}},
        {"winner":second_raw,"reasoning":"second","scores":{"A":.2,"B":.9}}])
    monkeypatch.setattr(phase,"pairwise_judge",mocked)
    result = phase.swap_and_average(Q,A,B,reference=REF)
    assert mocked.call_count == 2
    assert mocked.call_args_list[0].args[:3] == (Q,A,B)
    assert mocked.call_args_list[1].args[:3] == (Q,B,A)
    assert result.winner_pass2 == ("A" if second_raw=="B" else "B")
    assert result.final_winner == expected and result.position_consistent is consistent
    assert result.scores_pass2 == {"A":.9,"B":.2}


@pytest.mark.parametrize("judge,human,expected", [
    ([1,0,1,0],[1,0,1,0],1), ([1,0,1,0],[0,1,0,1],-1),
    ([1,1,0,0],[1,0,1,0],0)])
def test_kappa_exact(judge,human,expected):
    assert phase.cohen_kappa(judge,human) == pytest.approx(expected)


@pytest.mark.parametrize("judge,human", [
    ([1], []), ([], []), ([True], [1]), ([0.0], [0]), ([2], [0]), (["1"], [1]),
    ([1,1],[1,1]),
])
def test_kappa_rejects_misaligned_or_nonbinary_labels(judge,human):
    with pytest.raises((ValueError, TypeError)):
        phase.cohen_kappa(judge,human)


def test_bias_known_counts():
    rows = [
        phase.JudgeResult(Q,A,B,"A","A","A","r1","r2",True),
        phase.JudgeResult(Q,A,B,"A","B","tie","r1","r2",False)]
    result = phase.bias_report(rows)
    assert result["total_judged"] == 2 and result["position_bias_count"] == 1
    assert result["position_bias_rate"] == .5 and result["verbosity_bias"] == 1
    assert result["interpretation"].strip()


def test_bias_empty():
    result=phase.bias_report([])
    assert result["total_judged"] == 0
    assert result["position_bias_rate"] == 0
    assert result["position_bias_count"] == 0
    assert result["verbosity_bias"] == 0
    assert result["verbosity_details"] == {
        "a_wins_a_longer":0,"b_wins_b_longer":0,"total_decisive":0}
    assert result["interpretation"].strip()
