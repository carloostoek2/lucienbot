"""Unit tests for broadcast text formatting (native entities + HTML)."""

from types import SimpleNamespace

from aiogram.types import MessageEntity

from services.broadcast.text_format import (
    extract_message_text_and_entities,
    resolve_broadcast_text_to_html,
)


class TestResolveBroadcastTextToHtml:
    def test_empty_text(self):
        assert resolve_broadcast_text_to_html("") == ""
        assert resolve_broadcast_text_to_html(None) == ""

    def test_native_bold_and_italic(self):
        entities = [
            MessageEntity(type="bold", offset=0, length=4),
            MessageEntity(type="italic", offset=5, length=5),
        ]
        assert resolve_broadcast_text_to_html("hola mundo", entities) == "<b>hola</b> <i>mundo</i>"

    def test_manual_html_preserved(self):
        raw = "Hola <b>reino</b> y <i>Diana</i>"
        assert resolve_broadcast_text_to_html(raw) == raw

    def test_plain_text_escapes_angle_brackets(self):
        assert resolve_broadcast_text_to_html("a < b & c") == "a &lt; b &amp; c"

    def test_code_and_link_entities(self):
        entities = [
            MessageEntity(type="code", offset=0, length=3),
            MessageEntity(type="text_link", offset=4, length=4, url="https://t.me"),
        ]
        result = resolve_broadcast_text_to_html("foo link", entities)
        assert result == '<code>foo</code> <a href="https://t.me">link</a>'


class TestExtractMessageTextAndEntities:
    def test_from_text_with_entities(self):
        ents = [MessageEntity(type="bold", offset=0, length=1)]
        msg = SimpleNamespace(text="X", entities=ents, caption=None, caption_entities=None)
        text, out = extract_message_text_and_entities(msg)
        assert text == "X"
        assert out == ents

    def test_from_caption(self):
        ents = [MessageEntity(type="italic", offset=0, length=3)]
        msg = SimpleNamespace(text=None, entities=None, caption="abc", caption_entities=ents)
        text, out = extract_message_text_and_entities(msg)
        assert text == "abc"
        assert out == ents

    def test_empty_message(self):
        msg = SimpleNamespace(text=None, entities=None, caption=None, caption_entities=None)
        assert extract_message_text_and_entities(msg) == ("", None)
