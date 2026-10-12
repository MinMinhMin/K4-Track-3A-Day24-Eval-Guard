from __future__ import annotations

"""Phase C: Production Guardrails — Presidio PII + NeMo Guardrails + P95 Latency."""

import asyncio
import json
import math
import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ADVERSARIAL_SET_PATH, GUARDRAILS_CONFIG_DIR, LATENCY_BUDGET_P95_MS, PRESIDIO_LANGUAGE


# ─── Task 9a: Presidio PII Detection ─────────────────────────────────────────

# Keep the general English NER recognizers (for example PERSON and
# US_DRIVER_LICENSE) out of Vietnamese policy questions. The lab only requires
# these contact and national-ID entities.
PII_ENTITIES = ("EMAIL_ADDRESS", "PHONE_NUMBER", "VN_CCCD", "VN_PHONE")

def setup_presidio():
    """Khởi tạo Presidio engine với custom Vietnamese PII recognizers. (Đã implement sẵn)

    Custom recognizers thêm vào:
        VN_CCCD  — số CCCD 12 chữ số hoặc CMND 9 chữ số
        VN_PHONE — số điện thoại Việt Nam (0[3-9]xxxxxxxx)

    Các recognizers mặc định đã có sẵn: EMAIL, PHONE_NUMBER (international), ...
    """
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, Pattern, PatternRecognizer
    from presidio_anonymizer import AnonymizerEngine

    cccd_recognizer = PatternRecognizer(
        supported_entity="VN_CCCD",
        patterns=[
            Pattern("CCCD 12 digits", r"\b\d{12}\b", 0.9),
            Pattern("CMND 9 digits",  r"\b\d{9}\b",  0.7),
        ],
    )
    phone_recognizer = PatternRecognizer(
        supported_entity="VN_PHONE",
        patterns=[Pattern("VN mobile", r"\b0[3-9]\d{8}\b", 0.9)],
    )

    registry = RecognizerRegistry()
    registry.load_predefined_recognizers()
    registry.add_recognizer(cccd_recognizer)
    registry.add_recognizer(phone_recognizer)

    analyzer  = AnalyzerEngine(registry=registry)
    anonymizer = AnonymizerEngine()
    return analyzer, anonymizer


def pii_scan(text: str, analyzer=None, anonymizer=None) -> dict:
    """Task 9a: Quét PII trong văn bản bằng Presidio.

    Returns:
        {
          "has_pii":    bool,
          "entities":   [{"type": str, "text": str, "score": float, "start": int, "end": int}],
          "anonymized": str,   # text với PII được thay bằng <TYPE>
        }
    """
    if not isinstance(text, str):
        raise TypeError("PII scan input must be a string.")
    if analyzer is None or anonymizer is None:
        configured_analyzer, configured_anonymizer = setup_presidio()
        if analyzer is None:
            analyzer = configured_analyzer
        if anonymizer is None:
            anonymizer = configured_anonymizer

    findings = analyzer.analyze(
        text=text,
        language=PRESIDIO_LANGUAGE,
        entities=list(PII_ENTITIES),
    )
    if findings is None:
        raise ValueError("Presidio returned no detection result object.")
    entities = []
    for finding in findings:
        start, end = finding.start, finding.end
        score = finding.score
        if (type(start) is not int or type(end) is not int or
                not 0 <= start < end <= len(text)):
            raise ValueError("Presidio returned an invalid entity span.")
        if (isinstance(score, bool) or not isinstance(score, (int, float)) or
                not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError("Presidio returned an invalid confidence score.")
        entities.append({
            "type": finding.entity_type,
            "text": text[start:end],
            "score": round(float(score), 3),
            "start": start,
            "end": end,
        })
    entities.sort(key=lambda row: (row["start"], row["end"], row["type"]))
    if not entities:
        return {"has_pii": False, "entities": [], "anonymized": text}
    anonymized = anonymizer.anonymize(text=text, analyzer_results=findings).text
    if not isinstance(anonymized, str):
        raise ValueError("Presidio anonymizer returned no text.")
    return {"has_pii": True, "entities": entities, "anonymized": anonymized}


# ─── Task 9b + 11: NeMo Guardrails ───────────────────────────────────────────

def setup_nemo_rails():
    """Khởi tạo NeMo Guardrails từ guardrails/config.yml. (Đã implement sẵn)

    Config directory: guardrails/
        config.yml  — model + rails config
        rails.co    — câu từ chối Colang 1.0; built-in self-check flows được bật trong YAML
    """
    from nemoguardrails import RailsConfig, LLMRails
    config = RailsConfig.from_path(GUARDRAILS_CONFIG_DIR)
    rails  = LLMRails(config)
    return rails


async def check_input_rail(text: str, rails=None) -> dict:
    """Task 9b: Kiểm tra input qua NeMo input rails (topic guard + jailbreak guard).

    Returns:
        {
          "allowed":        bool,
          "blocked_reason": str | None,
          "response":       str,          # NeMo's raw response
        }
    """
    if not isinstance(text, str):
        raise TypeError("NeMo input must be a string.")
    if rails is None:
        rails = setup_nemo_rails()
    result = await rails.generate_async(
        messages=[{"role": "user", "content": text}],
        options={"rails": ["input"], "log": {"activated_rails": True}},
    )
    response = _response_text(result)
    blocked = _activated_rail_decision(result)
    return {
        "allowed": not blocked,
        "blocked_reason": "nemo_input_rail" if blocked else None,
        "response": response,
    }


async def check_output_rail(question: str, answer: str, rails=None) -> dict:
    """Task 11: Kiểm tra LLM output qua NeMo output rails trước khi trả về user.

    NeMo output rails hoạt động trong context của cả cuộc hội thoại (input + output).
    Kiểm tra PII và nội dung nhạy cảm. Self-check này không thay RAGAS faithfulness
    hoặc kiểm tra factual accuracy với retrieved contexts.

    Returns:
        {
          "safe":           bool,
          "flagged_reason": str | None,
          "final_answer":   str,          # answer đã qua guard (có thể bị redact)
        }
    """
    if not isinstance(question, str) or not isinstance(answer, str):
        raise TypeError("NeMo output question and answer must be strings.")
    if rails is None:
        rails = setup_nemo_rails()
    result = await rails.generate_async(
        messages=[
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ],
        options={"rails": ["output"], "log": {"activated_rails": True}},
    )
    response = _response_text(result)
    blocked = _activated_rail_decision(result)
    return {
        "safe": not blocked,
        "flagged_reason": "nemo_output_rail" if blocked else None,
        "final_answer": response if blocked else answer,
    }


def _activated_rail_decision(result) -> bool:
    """Require NeMo's requested activation evidence; never infer from wording."""
    log = getattr(result, "log", None)
    if log is None or not hasattr(log, "activated_rails"):
        raise ValueError("NeMo result is missing log.activated_rails evidence.")
    activated = log.activated_rails
    if not isinstance(activated, (list, tuple)):
        raise ValueError("NeMo log.activated_rails must be a list.")
    blocked = False
    for rail in activated:
        stop = getattr(rail, "stop", None)
        if type(stop) is not bool:
            raise ValueError("NeMo activated rail is missing a boolean stop decision.")
        blocked = blocked or stop
    return blocked


def _response_text(result) -> str:
    responses = getattr(result, "response", None)
    if not isinstance(responses, (list, tuple)) or not responses:
        raise ValueError("NeMo result is missing its response message.")
    first = responses[0]
    content = first.get("content") if isinstance(first, dict) else getattr(first, "content", None)
    if not isinstance(content, str):
        raise ValueError("NeMo response content must be text.")
    return content


# ─── Task 10: Adversarial Test Suite ─────────────────────────────────────────

def run_adversarial_suite(adversarial_set: list[dict], rails=None,
                           analyzer=None, anonymizer=None) -> list[dict]:
    """Task 10: Chạy 20 adversarial inputs qua full guard stack, so sánh với expected.

    Guard stack order:
        1. pii_scan()         → block nếu has_pii (cho category pii_injection)
        2. check_input_rail() → block nếu jailbreak / off-topic / prompt injection

    Returns:
        list of {
          "id": int, "category": str, "input": str,
          "expected": "blocked"|"allowed",
          "actual":   "blocked"|"allowed",
          "blocked_by": str | None,       # "presidio" | "nemo_input" | None
          "passed": bool,
        }
    """
    if not isinstance(adversarial_set, list):
        raise TypeError("Adversarial set must be a list.")
    if not adversarial_set:
        return []
    required = {"id", "category", "input", "expected"}
    if any(not isinstance(item, dict) or not required.issubset(item) for item in adversarial_set):
        raise ValueError("Each adversarial case must include id, category, input, and expected.")
    if analyzer is None or anonymizer is None:
        configured_analyzer, configured_anonymizer = setup_presidio()
        if analyzer is None:
            analyzer = configured_analyzer
        if anonymizer is None:
            anonymizer = configured_anonymizer
    if rails is None:
        rails = setup_nemo_rails()

    async def _evaluate():
        rows = []
        for item in adversarial_set:
            pii = pii_scan(item["input"], analyzer, anonymizer)
            blocked_by = "presidio" if pii["has_pii"] else None
            if blocked_by is None:
                rail = await check_input_rail(item["input"], rails)
                if not rail["allowed"]:
                    blocked_by = "nemo_input"
            actual = "blocked" if blocked_by else "allowed"
            rows.append({
                "id": item["id"],
                "category": item["category"],
                "input": item["input"],
                "expected": item["expected"],
                "actual": actual,
                "blocked_by": blocked_by,
                "passed": actual == item["expected"],
            })
        return rows

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_evaluate())
    raise RuntimeError("run_adversarial_suite cannot run inside an active event loop.")


# ─── Task 12: P95 Latency Measurement ────────────────────────────────────────

def measure_p95_latency(test_inputs: list[str], n_runs: int = 20,
                         rails=None, analyzer=None, anonymizer=None) -> dict:
    """Task 12: measure INPUT layers sequentially, not end-to-end guard/RAG latency.

    Reuse engines. Inside ONE event loop, execute two real warm-up calls per layer,
    excluded from samples. Then collect exactly n_runs timed samples (cycle clean
    inputs), always measuring BOTH PII and NeMo input even if PII blocks.
    Use perf_counter; keep raw milliseconds. summarize_latency() supplies linear
    percentiles at (n - 1) * q. Submission requires n_runs >= 20.
    Short-circuit request timing, RAG and output timing are outside this scope.
    """
    from src.experiment_support import summarize_latency

    if not isinstance(test_inputs, list) or not test_inputs or any(
            not isinstance(text, str) or not text.strip() for text in test_inputs):
        raise ValueError("Latency measurement requires a non-empty list of text inputs.")
    if type(n_runs) is not int or n_runs < 20:
        raise ValueError("Latency measurement requires at least 20 timed samples.")
    if analyzer is None or anonymizer is None:
        configured_analyzer, configured_anonymizer = setup_presidio()
        if analyzer is None:
            analyzer = configured_analyzer
        if anonymizer is None:
            anonymizer = configured_anonymizer
    if rails is None:
        rails = setup_nemo_rails()

    async def _measure():
        # Warm both layers twice and exclude these calls from the timed sample list.
        for index in range(2):
            text = test_inputs[index % len(test_inputs)]
            pii_scan(text, analyzer, anonymizer)
            await check_input_rail(text, rails)

        samples = []
        for index in range(n_runs):
            text = test_inputs[index % len(test_inputs)]
            started = time.perf_counter()
            pii_scan(text, analyzer, anonymizer)
            after_pii = time.perf_counter()
            await check_input_rail(text, rails)
            finished = time.perf_counter()
            presidio_ms = (after_pii - started) * 1000
            nemo_ms = (finished - after_pii) * 1000
            samples.append({
                "presidio_ms": presidio_ms,
                "nemo_input_ms": nemo_ms,
                "input_guard_ms": presidio_ms + nemo_ms,
            })
        return samples

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return summarize_latency(asyncio.run(_measure()), warmup_runs=2)
    raise RuntimeError("measure_p95_latency cannot run inside an active event loop.")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from scripts.run_experiments import main
    raise SystemExit(main(["--phase", "c", *sys.argv[1:]]))
