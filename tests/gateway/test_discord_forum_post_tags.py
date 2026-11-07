"""A forum post's tags reach the agent in ``Channel Topic``, and a tag edit re-renders it.

Forum tags label what a post is about (whose health question, which kind of job thread). The
agent only sees the session context, so the tags ride on the forum topic it already shows."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import gateway.run as gateway_run
import plugins.platforms.discord.adapter as discord_platform
from gateway.config import GatewayConfig, Platform, PlatformConfig
from gateway.session import build_session_context
from plugins.platforms.discord.adapter import DiscordAdapter

_BOT = SimpleNamespace(id=999)


class _Thread:
    def __init__(self, parent: SimpleNamespace, tags: list[str]) -> None:
        self.id, self.name, self.parent, self.parent_id = 800, "set up profiles", parent, parent.id
        self.guild, self.archived, self.topic = parent.guild, False, None
        self.applied_tags = [SimpleNamespace(name=t) for t in tags]


def _message(channel: object, message_id: int) -> SimpleNamespace:
    return SimpleNamespace(
        id=message_id, content="<@999> hello", mentions=[_BOT], attachments=[], reference=None,
        created_at=datetime.now(UTC), channel=channel,
        author=SimpleNamespace(id=42, display_name="Dim", name="dim"))


def _adapter(monkeypatch: pytest.MonkeyPatch, thread: _Thread) -> DiscordAdapter:
    monkeypatch.setattr(discord_platform.discord, "Thread", _Thread, raising=False)
    monkeypatch.setenv("DISCORD_AUTO_THREAD", "false")
    adapter = DiscordAdapter(PlatformConfig(enabled=True, token="fake"))
    adapter._client = SimpleNamespace(user=_BOT, get_channel=lambda _: thread)
    adapter._text_batch_delay_seconds = 0
    adapter._discord_history_backfill = lambda: False
    adapter.handle_message = AsyncMock()
    return adapter


def _parent(*, forum: bool) -> SimpleNamespace:
    guild = SimpleNamespace(id=1, name="bro 231")
    return SimpleNamespace(id=700, name="health", topic="Health questions", guild=guild,
                           type=15 if forum else 0)


async def _prompt(adapter: DiscordAdapter, thread: _Thread, message_id: int) -> str:
    assert await adapter._handle_message(_message(thread, message_id))
    source = adapter.handle_message.await_args.args[0].source
    runner = object.__new__(gateway_run.GatewayRunner)
    config = GatewayConfig(platforms={Platform.DISCORD: PlatformConfig(enabled=True, token="x")})
    return runner._pinned_session_context_prompt(build_session_context(source, config), False, None)


@pytest.mark.asyncio
async def test_forum_post_tags_appear_and_follow_edits(monkeypatch: pytest.MonkeyPatch) -> None:
    thread = _Thread(_parent(forum=True), ["dim", "ana"])
    adapter = _adapter(monkeypatch, thread)

    first = await _prompt(adapter, thread, 100)
    assert "Health questions | Post tags: dim, ana" in first

    thread.applied_tags = [SimpleNamespace(name="research")]
    second = await _prompt(adapter, thread, 101)
    assert "Post tags: research" in second and "dim, ana" not in second


@pytest.mark.asyncio
async def test_untagged_forum_post_and_plain_thread_keep_their_topic(monkeypatch: pytest.MonkeyPatch) -> None:
    for forum in (True, False):
        thread = _Thread(_parent(forum=forum), [] if forum else ["ignored"])
        prompt = await _prompt(_adapter(monkeypatch, thread), thread, 100)
        assert "Post tags" not in prompt
        assert ("Health questions" in prompt) is forum
