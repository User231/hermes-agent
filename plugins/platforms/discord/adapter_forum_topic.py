"""The topic a Discord channel shows the agent; forum posts also carry their tags."""
from __future__ import annotations

from typing import Any, Callable, Optional


def effective_topic(channel: Any, *, is_thread: bool, is_forum: Callable[[Any], bool]) -> Optional[str]:
    """The channel's topic. A forum post falls back to its forum's topic and appends the post's tags.

    Forum tags label what a post is about (for example which person it concerns), so they reach the
    agent through ``Channel Topic``. That field is part of the pinned session context, which
    re-renders when it changes, so a tag edited mid-conversation shows up on the next turn."""
    topic = getattr(channel, "topic", None)
    parent = getattr(channel, "parent", None) if is_thread else None
    if parent is None or not is_forum(parent):
        return topic
    topic = topic or getattr(parent, "topic", None)
    tags = ", ".join(tag.name for tag in getattr(channel, "applied_tags", None) or ())
    if not tags:
        return topic
    return f"{topic} | Post tags: {tags}" if topic else f"Post tags: {tags}"
