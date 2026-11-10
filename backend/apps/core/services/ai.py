"""AI provider boundary.

Providers (settings.AI_PROVIDER, chosen automatically from the configured keys):
  * "anthropic" — Claude via the official `anthropic` SDK (used when ANTHROPIC_API_KEY is set)
  * "openai"    — OpenAI via the official `openai` SDK (used when only OPENAI_API_KEY is set)
  * "dev_mock"  — no key configured. Output is prefixed with a visible development
                  notice so a mock response can never be mistaken for a real AI answer.

Both real providers stream text, report token usage, and raise AIError on any
failure or refusal so callers refund the student's credits.

Cost controls applied here:
  * per-purpose model + effort routing (admin-configurable via AIConfig)
  * hard output-token caps per purpose
  * prompt caching (explicit on Anthropic; automatic on OpenAI, keyed per purpose)
  * Anthropic server-side refusal fallbacks
"""
from __future__ import annotations

import hashlib
import logging
import math
import re
from dataclasses import dataclass, field
from typing import Iterator

from django.conf import settings

logger = logging.getLogger("kwado.ai")

DEV_NOTICE = "> **Development mode** — the AI provider is not configured, so this is a placeholder response, not real tutoring.\n\n"

FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AIError(Exception):
    """Raised when the AI call fails. Callers must refund any reserved credits."""


@dataclass
class AIResult:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    is_mock: bool = False
    meta: dict = field(default_factory=dict)


@dataclass
class Route:
    model: str
    effort: str
    max_tokens: int


# (effort, max output tokens) per purpose; the model comes from the active provider.
DEFAULT_ROUTES = {
    "tutor_chat": ("medium", 4000),
    "topic_explanation": ("low", 3000),
    "practice_set": ("medium", 6000),
    "document_analysis": ("high", 8000),
    "roadmap": ("medium", 6000),
}


def provider() -> str:
    return settings.AI_PROVIDER


def _model_belongs_to(model: str, prov: str) -> bool:
    return model.startswith("claude") == (prov == "anthropic")


def route_for(purpose: str) -> Route:
    """Admin overrides (AIConfig rows) win over code defaults.

    A model override is only applied when it belongs to the active provider
    (claude-* for Anthropic, anything else for OpenAI), so switching providers
    never sends a Claude model name to OpenAI or vice versa.
    """
    from apps.ai_tutor.models import AIConfig

    prov = provider()
    effort, max_tokens = DEFAULT_ROUTES.get(purpose, DEFAULT_ROUTES["tutor_chat"])
    model = settings.AI_OPENAI_MODEL if prov == "openai" else settings.AI_ANTHROPIC_MODEL
    cfg = AIConfig.get_cached(purpose)
    if cfg:
        if cfg.get("model") and _model_belongs_to(cfg["model"], prov):
            model = cfg["model"]
        effort = cfg.get("effort") or effort
        max_tokens = min(int(cfg.get("max_tokens") or max_tokens), settings.AI_MAX_OUTPUT_TOKENS * 4)
    return Route(model, effort, max_tokens)


_client = None
_openai_client = None


def _anthropic():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=120.0, max_retries=2)
    return _client


def _openai():
    global _openai_client
    if _openai_client is None:
        import openai

        _openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY, timeout=120.0, max_retries=2)
    return _openai_client


def _system_blocks(system: str):
    # Stable system prompt first, marked for caching. Volatile per-student
    # context is appended as a separate (uncached) block after it.
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def stream_completion(
    *, purpose: str, system: str, context: str, messages: list[dict]
) -> Iterator[str | AIResult]:
    """Yield text deltas, then a final AIResult. Raises AIError on failure."""
    route = route_for(purpose)
    prov = provider()
    if prov == "openai":
        yield from _openai_stream(route, purpose, system, context, messages)
        return
    if prov != "anthropic":
        yield from _mock_stream(purpose, messages, route)
        return

    import anthropic

    system_blocks = _system_blocks(system)
    if context:
        system_blocks.append({"type": "text", "text": context})
    try:
        with _anthropic().beta.messages.stream(
            model=route.model,
            max_tokens=route.max_tokens,
            system=system_blocks,
            messages=messages,
            output_config={"effort": route.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        ) as stream:
            for text in stream.text_stream:
                yield text
            final = stream.get_final_message()
    except anthropic.RateLimitError as e:
        raise AIError("rate_limited") from e
    except anthropic.APIStatusError as e:
        logger.exception("AI status error %s", getattr(e, "status_code", None))
        raise AIError("provider_error") from e
    except anthropic.APIConnectionError as e:
        raise AIError("connection_error") from e

    if final.stop_reason == "refusal":
        raise AIError("refused")
    text = "".join(b.text for b in final.content if getattr(b, "type", None) == "text")
    if not text.strip():
        raise AIError("empty_response")
    usage = final.usage
    yield AIResult(
        text=text,
        model=final.model,
        input_tokens=usage.input_tokens or 0,
        output_tokens=usage.output_tokens or 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        meta={"stop_reason": final.stop_reason},
    )


# --------------------------------------------------------------------------
# OpenAI (Chat Completions, streaming)
# --------------------------------------------------------------------------
REASONING_PREFIXES = ("gpt-5", "o1", "o3", "o4")


def _to_openai_content(content):
    """Convert our (Anthropic-shaped) content blocks to OpenAI chat content."""
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if block.get("type") == "text":
            parts.append({"type": "text", "text": block["text"]})
        elif block.get("type") == "image":
            src = block["source"]
            parts.append({"type": "image_url",
                          "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}})
    return parts


def _openai_stream(route: Route, purpose: str, system: str, context: str, messages: list[dict]):
    import openai

    instructions = system + (f"\n\n{context}" if context else "")
    chat = [{"role": "system", "content": instructions}]
    chat += [{"role": m["role"], "content": _to_openai_content(m["content"])} for m in messages]
    kwargs = {
        "model": route.model,
        "messages": chat,
        "stream": True,
        "stream_options": {"include_usage": True},
        "max_completion_tokens": route.max_tokens,
        # Stable per-purpose key improves OpenAI's automatic prompt-cache hit rate.
        "prompt_cache_key": f"kwado-{purpose}",
    }
    if route.model.startswith(REASONING_PREFIXES):
        # Reasoning tokens count against the cap, so leave headroom for the visible answer.
        kwargs["reasoning_effort"] = {"xhigh": "high", "max": "high"}.get(route.effort, route.effort)
        kwargs["max_completion_tokens"] = route.max_tokens + 8000

    parts, usage, finish, refused, model_name = [], None, None, False, route.model
    try:
        for chunk in _openai().chat.completions.create(**kwargs):
            model_name = chunk.model or model_name
            if chunk.usage:
                usage = chunk.usage
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            finish = choice.finish_reason or finish
            if choice.delta.refusal:
                refused = True
            if choice.delta.content:
                parts.append(choice.delta.content)
                yield choice.delta.content
    except openai.RateLimitError as e:
        raise AIError("rate_limited") from e
    except openai.APIStatusError as e:
        logger.exception("OpenAI status error %s", getattr(e, "status_code", None))
        raise AIError("provider_error") from e
    except openai.APIConnectionError as e:
        raise AIError("connection_error") from e

    if refused or finish == "content_filter":
        raise AIError("refused")
    text = "".join(parts)
    if not text.strip():
        raise AIError("empty_response")
    cached = 0
    if usage is not None and getattr(usage, "prompt_tokens_details", None):
        cached = usage.prompt_tokens_details.cached_tokens or 0
    yield AIResult(
        text=text,
        model=model_name,
        input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        output_tokens=getattr(usage, "completion_tokens", 0) or 0,
        cache_read_tokens=cached,
        meta={"stop_reason": finish, "provider": "openai"},
    )


def complete(*, purpose: str, system: str, context: str = "", messages: list[dict]) -> AIResult:
    result = None
    for chunk in stream_completion(purpose=purpose, system=system, context=context, messages=messages):
        if isinstance(chunk, AIResult):
            result = chunk
    if result is None:
        raise AIError("no_result")
    return result


# --------------------------------------------------------------------------
# Development mock — clearly labelled, deterministic, never used in prod.
# --------------------------------------------------------------------------
def _mock_stream(purpose, messages, route):
    last = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last = m["content"] if isinstance(m["content"], str) else str(m["content"])
            break
    if "FAIL_AI" in last:  # lets tests/dev exercise the refund path
        raise AIError("mock_failure")
    body = (
        DEV_NOTICE
        + (f"You asked: *{last[:160]}*\n\n" if purpose in ("tutor_chat", "topic_explanation", "practice_set") else "")
        + "When the AI provider is configured, Kwado's tutor will answer here with a step-by-step "
        "explanation grounded in your syllabus and approved materials.\n\n"
        "**Try this meanwhile:**\n1. Re-read the lesson summary.\n2. Attempt 5 practice questions on this topic.\n"
        "3. Review the explanations for any you miss."
    )
    for word in re.split(r"(\s+)", body):
        yield word
    yield AIResult(text=body, model="dev-mock", input_tokens=0, output_tokens=0, is_mock=True)


# --------------------------------------------------------------------------
# Embeddings for retrieval (pgvector): Voyage AI if VOYAGE_API_KEY is set,
# else OpenAI if OPENAI_API_KEY is set, else a hashed bag-of-words embedding
# (development). After changing embedding provider, re-process uploaded
# materials, since vectors from different models aren't comparable.
# --------------------------------------------------------------------------
def embed(texts: list[str], input_type: str = "document") -> list[list[float]]:
    import os

    dim = settings.EMBEDDING_DIMENSIONS
    key = os.environ.get("VOYAGE_API_KEY")
    if key:
        import requests

        r = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {key}"},
            json={"input": texts, "model": os.environ.get("VOYAGE_MODEL", "voyage-3"), "input_type": input_type},
            timeout=60,
        )
        r.raise_for_status()
        return [d["embedding"] for d in r.json()["data"]]
    if settings.OPENAI_API_KEY:
        resp = _openai().embeddings.create(
            model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"), input=texts, dimensions=dim)
        return [d.embedding for d in sorted(resp.data, key=lambda d: d.index)]
    out = []
    for t in texts:
        v = [0.0] * dim
        for tok in re.findall(r"[a-z0-9]+", t.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % dim] += 1.0 if (h >> 20) & 1 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out
