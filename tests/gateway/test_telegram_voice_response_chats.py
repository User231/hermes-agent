"""``voice_response_chats``: in listed groups a voice note counts as addressed to the bot.

Our own patch (not upstream). Kept in its own file so it never conflicts with upstream's edits to
``test_telegram_group_gating.py``, whose helpers it borrows.
"""

from types import SimpleNamespace

from tests.gateway.test_telegram_group_gating import _group_message, _make_adapter


def _voice_group_message(**kw):
    msg = _group_message(text=None, **kw)
    msg.voice = SimpleNamespace(file_id="v1", duration=3)
    return msg


def test_voice_response_chats_route_voice_notes_only_in_listed_groups():
    """A wake word can't be checked inside untranscribed audio, so a voice note in a listed group
    counts as addressed to the bot; other groups and text messages keep the mention rules."""
    adapter = _make_adapter(require_mention=True, mention_patterns=[r"^\s*bro\b"])
    adapter.config.extra["voice_response_chats"] = ["-100"]
    assert adapter._should_process_message(_voice_group_message(chat_id=-100)) is True
    assert adapter._should_process_message(_voice_group_message(chat_id=-200)) is False
    assert adapter._should_process_message(_group_message("hello", chat_id=-100)) is False
    assert adapter._should_process_message(_group_message("bro hello", chat_id=-100)) is True


def test_voice_needs_mention_without_voice_response_chats():
    adapter = _make_adapter(require_mention=True)
    assert adapter._should_process_message(_voice_group_message()) is False
