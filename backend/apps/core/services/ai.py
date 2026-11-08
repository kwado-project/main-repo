"""AI provider boundary.

Production uses Anthropic Claude through the official `anthropic` SDK.
When no API key is configured the `dev_mock` provider is used. Its output is
always prefixed with a visible development notice so a mock response can
never be mistaken for a real AI answer.

Cost controls applied here:
  * per-purpose model + effort routing (admin-configurable via AIConfig)
  * hard `max_tokens` caps per purpose
  * prompt caching on the large, stable system prompt
  * server-side refusal fallbacks so a refused request is re-served instead of
    failing (failed requests are refunded upstream anyway)
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


DEFAULT_ROUTES = {
    "tutor_chat": Route(settings.AI_DEFAULT_MODEL, "medium", 4000),
    "topic_explanation": Route(settings.AI_DEFAULT_MODEL, "low", 3000),
    "practice_set": Route(settings.AI_DEFAULT_MODEL, "medium", 6000),
    "document_analysis": Route(settings.AI_DEFAULT_MODEL, "high", 8000),
    "roadmap": Route(settings.AI_DEFAULT_MODEL, "medium", 6000),
}


def route_for(purpose: str) -> Route:
    """Admin overrides (AIConfig rows) win over code defaults."""
    from apps.ai_tutor.models import AIConfig

    base = DEFAULT_ROUTES.get(purpose, DEFAULT_ROUTES["tutor_chat"])
    cfg = AIConfig.get_cached(purpose)
    if not cfg:
        return base
    return Route(cfg.get("model") or base.model, cfg.get("effort") or base.effort,
                 min(int(cfg.get("max_tokens") or base.max_tokens), settings.AI_MAX_OUTPUT_TOKENS * 4))


_client = None


def _anthropic():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=120.0, max_retries=2)
    return _client


def _system_blocks(system: str):
    # Stable system prompt first, marked for caching. Volatile per-student
    # context is appended as a separate (uncached) block after it.
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def stream_completion(
    *, purpose: str, system: str, context: str, messages: list[dict]
) -> Iterator[str | AIResult]:
    """Yield text deltas, then a final AIResult. Raises AIError on failure."""
    route = route_for(purpose)
    if settings.AI_PROVIDER != "anthropic":
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
        + f"You asked: *{last[:200]}*\n\n"
        + "When the AI provider is configured, Kwado's tutor will answer here with a step-by-step "
        "explanation grounded in your syllabus and approved materials.\n\n"
        "**Try this meanwhile:**\n1. Re-read the lesson summary.\n2. Attempt 5 practice questions on this topic.\n"
        "3. Review the explanations for any you miss."
    )
    for word in re.split(r"(\s+)", body):
        yield word
    yield AIResult(text=body, model="dev-mock", input_tokens=0, output_tokens=0, is_mock=True)


# --------------------------------------------------------------------------
# Embeddings for retrieval (pgvector). Voyage AI in production, a hashed
# bag-of-words embedding in development.
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
    out = []
    for t in texts:
        v = [0.0] * dim
        for tok in re.findall(r"[a-z0-9]+", t.lower()):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            v[h % dim] += 1.0 if (h >> 20) & 1 else -1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / n for x in v])
    return out
