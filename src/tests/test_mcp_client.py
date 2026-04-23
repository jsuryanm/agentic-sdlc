"""Unit tests for the Context7 MCP helpers in src.tools.mcp_client.

Context7's MCP server is never actually launched — we inject fake LangChain
tools and patch the cache so the tests are fast and offline.
"""
import asyncio

import pytest

from src.tools import mcp_client


class _FakeTool:
    def __init__(self, name: str, responder):
        self.name = name
        self._responder = responder
        self.calls = []

    async def ainvoke(self, payload):
        self.calls.append(payload)
        return self._responder(payload)


def _install_fake_tools(monkeypatch, resolver_responder, docs_responder):
    tools = [
        _FakeTool('resolve-library-id', resolver_responder),
        _FakeTool('get-library-docs', docs_responder),
    ]

    async def fake_get_tools():
        return tools

    mcp_client.reset_context7_cache()
    monkeypatch.setattr(mcp_client, 'get_context7_tools', fake_get_tools)
    return tools


def test_fetch_docs_for_stack_happy_path(monkeypatch):
    _install_fake_tools(
        monkeypatch,
        resolver_responder=lambda p: '/tiangolo/fastapi is the top match',
        docs_responder=lambda p: f'DOCS for {p["libraryId"]} about {p["query"][:20]}',
    )

    out = asyncio.run(mcp_client.fetch_docs_for_stack(['fastapi']))

    assert '## fastapi' in out
    assert 'DOCS for /tiangolo/fastapi' in out


def test_fetch_docs_for_stack_caches_per_library(monkeypatch):
    tools = _install_fake_tools(
        monkeypatch,
        resolver_responder=lambda p: '/tiangolo/fastapi',
        docs_responder=lambda p: 'cached-doc',
    )

    asyncio.run(mcp_client.fetch_docs_for_stack(['fastapi']))
    asyncio.run(mcp_client.fetch_docs_for_stack(['fastapi']))

    resolver_calls = sum(1 for t in tools if t.name == 'resolve-library-id' for _ in t.calls)
    assert resolver_calls == 1, 'resolver should be invoked once thanks to the cache'


def test_fetch_docs_for_stack_returns_empty_on_resolver_miss(monkeypatch):
    _install_fake_tools(
        monkeypatch,
        resolver_responder=lambda p: 'no match found for that library',
        docs_responder=lambda p: 'should not be called',
    )

    out = asyncio.run(mcp_client.fetch_docs_for_stack(['not-a-real-lib']))
    assert out == ''


def test_fetch_docs_for_stack_handles_tool_failure(monkeypatch):
    def boom(_payload):
        raise RuntimeError('mcp died')

    _install_fake_tools(
        monkeypatch,
        resolver_responder=boom,
        docs_responder=lambda p: 'unused',
    )

    # Must not raise — the helper swallows tool errors and returns ''
    out = asyncio.run(mcp_client.fetch_docs_for_stack(['fastapi']))
    assert out == ''


def test_fetch_docs_for_stack_empty_stack_short_circuits(monkeypatch):
    # No tool installation — if the code reaches MCP, it would fail
    mcp_client.reset_context7_cache()
    assert asyncio.run(mcp_client.fetch_docs_for_stack([])) == ''


def test_fetch_docs_for_stack_respects_use_context7_flag(monkeypatch):
    monkeypatch.setattr(mcp_client.settings, 'USE_CONTEXT7', False)
    mcp_client.reset_context7_cache()
    assert asyncio.run(mcp_client.fetch_docs_for_stack(['fastapi'])) == ''


@pytest.fixture(autouse=True)
def _clear_cache():
    mcp_client.reset_context7_cache()
    yield
    mcp_client.reset_context7_cache()
