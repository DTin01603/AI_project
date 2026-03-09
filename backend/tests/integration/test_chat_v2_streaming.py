import json
import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

get_research_agent_graph = importlib.import_module("api.deps").get_research_agent_graph
create_app = importlib.import_module("main").create_app


class FakeGraph:
    def __init__(self, stream_scenarios: list[object]):
        self.stream_scenarios = stream_scenarios
        self.stream_calls = 0

    async def ainvoke(self, payload, request_id=None):  # pragma: no cover
        return {
            "final_answer": "ok",
            "citations": [],
            "execution_metadata": {"request_id": request_id, "conversation_id": payload.conversation_id},
        }

    def astream(self, payload, request_id=None):
        index = self.stream_calls
        self.stream_calls += 1
        scenario = self.stream_scenarios[index] if index < len(self.stream_scenarios) else self.stream_scenarios[-1]

        async def _generator():
            if isinstance(scenario, Exception):
                raise scenario
            for item in scenario:
                yield item

        return _generator()


def _stream_data_lines(client: TestClient, payload: dict[str, object]) -> tuple[list[str], dict[str, str]]:
    lines: list[str] = []
    with client.stream("POST", "/api/v2/chat?stream=true", json=payload) as response:
        assert response.status_code == 200
        for raw in response.iter_lines():
            if not raw:
                continue
            text = raw if isinstance(raw, str) else raw.decode("utf-8")
            if text.startswith("data: "):
                lines.append(text[6:])
        headers = dict(response.headers)
    return lines, headers


def _build_app_client(fake_graph: FakeGraph) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_research_agent_graph] = lambda: fake_graph
    return TestClient(app)


def _simple_success_updates() -> list[dict[str, dict[str, object]]]:
    return [
        {
            "entry": {
                "query_type": "simple",
                "execution_metadata": {
                    "request_id": "req-1",
                    "conversation_id": "conv-1",
                    "model": "gemini/gemini-2.5-flash",
                },
            }
        },
        {
            "simple_llm": {
                "query_type": "simple",
                "final_answer": "Xin chào",
                "citations": [],
                "execution_metadata": {
                    "request_id": "req-1",
                    "conversation_id": "conv-1",
                    "llm": {
                        "provider": "gemini",
                        "model": "gemini/gemini-2.5-flash",
                        "finish_reason": "stop",
                    },
                },
            }
        },
    ]


def test_stream_sse_sequence_status_done_done_marker() -> None:
    client = _build_app_client(FakeGraph([_simple_success_updates()]))

    data_lines, headers = _stream_data_lines(
        client,
        {
            "message": "Xin chào",
            "conversation_id": "conv-1",
            "model": "gemini/gemini-2.5-flash",
        },
    )

    assert headers.get("x-api-version") == "2"
    assert len(data_lines) >= 3

    parsed_events = [json.loads(item) for item in data_lines[:-1]]
    assert parsed_events[0]["type"] == "status"
    assert parsed_events[-1]["type"] == "done"
    assert parsed_events[-1]["data"]["answer"] == "Xin chào"
    assert data_lines[-1] == "[DONE]"


def test_stream_timeout_retries_once_then_succeeds() -> None:
    first_failure = TimeoutError("model timed out")
    client = _build_app_client(FakeGraph([first_failure, _simple_success_updates()]))

    data_lines, _ = _stream_data_lines(
        client,
        {
            "message": "Test retry",
            "conversation_id": "conv-retry",
            "model": "gemini/gemini-2.5-flash",
        },
    )

    parsed_events = [json.loads(item) for item in data_lines[:-1]]
    retry_events = [event for event in parsed_events if event.get("node") == "retry"]
    done_events = [event for event in parsed_events if event.get("type") == "done"]

    assert len(retry_events) == 1
    assert retry_events[0]["data"]["attempt"] == 2
    assert len(done_events) == 1
    assert done_events[0]["data"]["error"] is None
    assert data_lines[-1] == "[DONE]"


def test_stream_quota_error_emits_done_error_and_done_marker() -> None:
    quota_failure = RuntimeError("RESOURCE_EXHAUSTED: quota exceeded 429")
    client = _build_app_client(FakeGraph([quota_failure, quota_failure]))

    data_lines, _ = _stream_data_lines(
        client,
        {
            "message": "Test quota",
            "conversation_id": "conv-quota",
            "model": "gemini/gemini-2.5-flash",
        },
    )

    parsed_events = [json.loads(item) for item in data_lines[:-1]]
    retry_events = [event for event in parsed_events if event.get("node") == "retry"]
    done_events = [event for event in parsed_events if event.get("type") == "done"]

    assert len(retry_events) == 1
    assert len(done_events) == 1
    assert done_events[0]["data"]["error"]["code"] == "MODEL_ERROR"
    assert "quota" in done_events[0]["data"]["error"]["message"].lower()
    assert data_lines[-1] == "[DONE]"
