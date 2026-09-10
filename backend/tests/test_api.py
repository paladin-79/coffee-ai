"""End-to-end API behaviour with a fake LLM provider (no network)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.llm.base import LLMProvider
from app.llm.schemas import LLMResponse, LLMTransportError
from app.main import create_app
from app.store.memory import InMemoryStore

PUBLIC_KEYS = {"title", "tagline", "instructions_vi", "instructions_en", "max_attempts"}


class FakeProvider(LLMProvider):
    def __init__(
        self,
        *,
        recommendation: str | None = "egg_coffee",
        reply: str = "Cà phê trứng nhé.",
        raise_transport: bool = False,
    ) -> None:
        self.recommendation = recommendation
        self.reply = reply
        self.raise_transport = raise_transport

    async def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if self.raise_transport:
            raise LLMTransportError("simulated outage")
        return LLMResponse(
            recommendation=self.recommendation,
            reply=self.reply,
            raw="{}",
            input_tokens=10,
            output_tokens=5,
        )


def client_with(provider: FakeProvider) -> TestClient:
    return TestClient(create_app(llm_provider=provider, store=InMemoryStore()))


def test_challenge_exposes_only_the_public_block() -> None:
    with client_with(FakeProvider()) as client:
        body = client.get("/api/challenge").json()
    assert set(body) == PUBLIC_KEYS
    assert "target" not in body
    assert "solution_paths" not in body
    assert "guardrails" not in body


def test_health() -> None:
    with client_with(FakeProvider()) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_chat_on_unknown_session_is_404() -> None:
    with client_with(FakeProvider()) as client:
        r = client.post("/api/chat", json={"session_id": "nope", "prompt": "hi"})
    assert r.status_code == 404


def test_win_path() -> None:
    provider = FakeProvider(recommendation="iced_milk_coffee", reply="Trời nóng thì sữa đá.")
    with client_with(provider) as client:
        session = client.post("/api/session", json={}).json()
        r = client.post(
            "/api/chat",
            json={"session_id": session["session_id"], "prompt": "Hà Nội 38 độ, đang vội."},
        ).json()
    assert r["success"] is True
    assert r["status"] == "won"
    assert r["attempt"] == 1
    assert r["attempts_remaining"] == session["max_attempts"] - 1


def test_finished_session_rejects_further_chat() -> None:
    provider = FakeProvider(recommendation="iced_milk_coffee")
    with client_with(provider) as client:
        session = client.post("/api/session", json={}).json()
        client.post("/api/chat", json={"session_id": session["session_id"], "prompt": "x"})
        r = client.post("/api/chat", json={"session_id": session["session_id"], "prompt": "x"})
    assert r.status_code == 409


def test_transport_error_does_not_consume_an_attempt() -> None:
    provider = FakeProvider(raise_transport=True)
    with client_with(provider) as client:
        session = client.post("/api/session", json={}).json()
        failed = client.post(
            "/api/chat", json={"session_id": session["session_id"], "prompt": "x"}
        )
        assert failed.status_code == 503

        provider.raise_transport = False
        provider.recommendation = "egg_coffee"
        r = client.post(
            "/api/chat", json={"session_id": session["session_id"], "prompt": "x"}
        ).json()
    assert r["attempt"] == 1  # the 503 did not count


def test_running_out_of_attempts_marks_the_session_lost() -> None:
    provider = FakeProvider(recommendation="egg_coffee")
    with client_with(provider) as client:
        session = client.post("/api/session", json={}).json()
        last = None
        for _ in range(session["max_attempts"]):
            last = client.post(
                "/api/chat", json={"session_id": session["session_id"], "prompt": "x"}
            ).json()
        assert last["status"] == "lost"
        assert last["attempts_remaining"] == 0

        blocked = client.post(
            "/api/chat", json={"session_id": session["session_id"], "prompt": "x"}
        )
    assert blocked.status_code == 409


def test_unreadable_answer_still_counts_and_has_a_reply() -> None:
    provider = FakeProvider(recommendation="cappuccino", reply="")
    with client_with(provider) as client:
        session = client.post("/api/session", json={}).json()
        r = client.post(
            "/api/chat", json={"session_id": session["session_id"], "prompt": "x"}
        ).json()
    assert r["success"] is False
    assert r["recommendation"] is None
    assert r["reply"]  # non-empty fallback
    assert r["attempt"] == 1
