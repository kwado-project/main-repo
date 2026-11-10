import importlib
from types import SimpleNamespace as NS
from unittest import mock

import pytest
from django.test import override_settings

from apps.core.services import ai


def _reload_settings(monkeypatch, **env):
    import config.settings as s
    for k in ("AI_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    importlib.reload(s)
    return s


@pytest.fixture
def restore_settings(monkeypatch):
    yield
    import config.settings as s
    for k in ("AI_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    importlib.reload(s)


def test_provider_auto_selection(monkeypatch, restore_settings):
    assert _reload_settings(monkeypatch).AI_PROVIDER == "dev_mock"
    s = _reload_settings(monkeypatch, OPENAI_API_KEY="sk-x")
    assert s.AI_PROVIDER == "openai" and s.AI_DEFAULT_MODEL == "gpt-5.5"
    s = _reload_settings(monkeypatch, ANTHROPIC_API_KEY="sk-ant-x", OPENAI_API_KEY="sk-x")
    assert s.AI_PROVIDER == "anthropic" and s.AI_DEFAULT_MODEL == "claude-opus-5-5"  # Anthropic wins when both set
    assert _reload_settings(monkeypatch, AI_PROVIDER="openai", ANTHROPIC_API_KEY="a", OPENAI_API_KEY="b").AI_PROVIDER == "openai"
    with pytest.raises(RuntimeError, match="key is not set"):
        _reload_settings(monkeypatch, AI_PROVIDER="openai")


def _chunk(content=None, finish=None, refusal=None, usage=None, choices=True):
    ch = [NS(delta=NS(content=content, refusal=refusal), finish_reason=finish)] if choices else []
    return NS(model="gpt-5.5-2026-04-23", choices=ch, usage=usage)


OPENAI = dict(AI_PROVIDER="openai", OPENAI_API_KEY="sk-test", AI_OPENAI_MODEL="gpt-5.5")


@pytest.mark.django_db
@override_settings(**OPENAI)
def test_openai_streams_text_and_usage(monkeypatch):
    usage = NS(prompt_tokens=120, completion_tokens=30, prompt_tokens_details=NS(cached_tokens=100))
    client = mock.MagicMock()
    client.chat.completions.create.return_value = iter([
        _chunk("Osmosis is "), _chunk("water movement."), _chunk(finish="stop"), _chunk(usage=usage, choices=False)])
    monkeypatch.setattr(ai, "_openai", lambda: client)
    out = list(ai.stream_completion(purpose="tutor_chat", system="SYS", context="CTX",
                                    messages=[{"role": "user", "content": "What is osmosis?"}]))
    assert out[:2] == ["Osmosis is ", "water movement."]
    res = out[-1]
    assert isinstance(res, ai.AIResult) and res.text == "Osmosis is water movement."
    assert (res.input_tokens, res.output_tokens, res.cache_read_tokens) == (120, 30, 100)
    kw = client.chat.completions.create.call_args.kwargs
    assert kw["model"] == "gpt-5.5" and kw["stream"] is True and kw["reasoning_effort"] == "medium"
    assert kw["messages"][0] == {"role": "system", "content": "SYS\n\nCTX"}


@pytest.mark.django_db
@override_settings(**OPENAI)
def test_openai_refusal_and_errors_raise_aierror(monkeypatch):
    import httpx2 as httpx
    import openai
    client = mock.MagicMock()
    monkeypatch.setattr(ai, "_openai", lambda: client)
    client.chat.completions.create.return_value = iter([_chunk(refusal="I can't help with that."), _chunk(finish="stop")])
    with pytest.raises(ai.AIError, match="refused"):
        list(ai.stream_completion(purpose="tutor_chat", system="S", context="", messages=[{"role": "user", "content": "x"}]))
    req = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    client.chat.completions.create.side_effect = openai.RateLimitError("slow down", response=httpx.Response(429, request=req), body=None)
    with pytest.raises(ai.AIError, match="rate_limited"):
        list(ai.stream_completion(purpose="tutor_chat", system="S", context="", messages=[{"role": "user", "content": "x"}]))


@pytest.mark.django_db
@override_settings(**OPENAI)
def test_openai_ignores_claude_model_override_and_converts_images(monkeypatch):
    from apps.ai_tutor.models import AIConfig
    AIConfig.objects.update_or_create(purpose="document_analysis", defaults={"model": "claude-opus-5-5", "effort": "max"})
    client = mock.MagicMock()
    client.chat.completions.create.return_value = iter([_chunk("ok"), _chunk(finish="stop")])
    monkeypatch.setattr(ai, "_openai", lambda: client)
    img = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "AAAA"}},
           {"type": "text", "text": "Analyse"}]
    list(ai.stream_completion(purpose="document_analysis", system="S", context="", messages=[{"role": "user", "content": img}]))
    kw = client.chat.completions.create.call_args.kwargs
    assert kw["model"] == "gpt-5.5" and kw["reasoning_effort"] == "high"
    assert kw["messages"][1]["content"][0] == {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAAA"}}


@pytest.mark.django_db
@override_settings(**OPENAI)
def test_tutor_refunds_when_openai_fails(seeded, make_student, auth, monkeypatch):
    import openai
    client = mock.MagicMock()
    client.chat.completions.create.side_effect = openai.APIConnectionError(request=mock.MagicMock())
    monkeypatch.setattr(ai, "_openai", lambda: client)
    u = make_student("oa@example.com")
    api = auth(u)
    conv = api.post("/api/ai/conversations/", {}, format="json").data
    body = b"".join(api.post(f"/api/ai/conversations/{conv['id']}/messages/", {"content": "hi"}, format="json").streaming_content).decode()
    assert "event: error" in body
    assert api.get("/api/wallet/").data["balance"] == 100
