import json
import httpx
from activity_planner.gemini_planner import GeminiClient, GeminiClientConfig, GeminiError


def test_gemini_client_parses_json_response():
    def handler(request: httpx.Request):
        data = {
            "candidates": [
                {"content": {"parts": [{"text": '{"category": "Coding", "confidence": 0.83}'}]}}
            ]
        }
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    client = GeminiClient(GeminiClientConfig(api_key="test-key"), transport=transport)
    result = client.classify_title("main.py - VSCode", ["Coding", "Reading"])
    assert result["category"] == "Coding"
    assert 0.8 < result["confidence"] < 0.9


def test_gemini_client_rate_limit_retry():
    calls = {"n": 0}

    def handler(request: httpx.Request):
        calls["n"] += 1
        if calls["n"] < 2:
            return httpx.Response(429, text="Too Many Requests")
        data = {"candidates": [{"content": {"parts": [{"text": '{"category": "Other", "confidence": 0.1}'}]}}]}
        return httpx.Response(200, json=data)

    transport = httpx.MockTransport(handler)
    client = GeminiClient(GeminiClientConfig(api_key="k", max_retries=2, backoff_base=0.01), transport=transport)
    result = client.classify_title("Random", ["Coding"])  # should retry once
    assert result["category"] == "Other"
    assert calls["n"] == 2


def test_gemini_client_failure_after_retries():
    def handler(request: httpx.Request):
        return httpx.Response(500, text="Server Error")

    transport = httpx.MockTransport(handler)
    client = GeminiClient(GeminiClientConfig(api_key="k", max_retries=1, backoff_base=0.01), transport=transport)
    try:
        client.classify_title("Title", ["Coding"])
    except Exception as e:
        assert isinstance(e, Exception)
    else:
        assert False, "Expected exception"
