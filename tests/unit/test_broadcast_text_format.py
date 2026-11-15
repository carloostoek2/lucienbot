"""Unit tests for broadcast text formatting (native entities + HTML)."""

from types import SimpleNamespace

from aiogram.types import MessageEntity

from services.broadcast.text_format import (
    extract_message_text_and_entities,
    measure_telegram_text_length,
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

    def test_loose_lt_escaped_while_tags_kept(self):
        """Regresión: un '<' suelto junto a etiquetas válidas ya no llega crudo a Telegram."""
        raw = "Hola <b>reino</b> y 5 < 10"
        assert resolve_broadcast_text_to_html(raw) == "Hola <b>reino</b> y 5 &lt; 10"

    def test_emoticon_heart_escaped_while_tags_kept(self):
        assert resolve_broadcast_text_to_html("<b>Te quiero</b> <3") == "<b>Te quiero</b> &lt;3"

    def test_unsupported_tag_escaped_while_tags_kept(self):
        assert (
            resolve_broadcast_text_to_html("<b>ok</b> <br> salto") == "<b>ok</b> &lt;br&gt; salto"
        )

    def test_link_tag_with_attributes_preserved(self):
        raw = '<a href="https://t.me/divan">El Diván</a> y 3 < 4'
        assert (
            resolve_broadcast_text_to_html(raw)
            == '<a href="https://t.me/divan">El Diván</a> y 3 &lt; 4'
        )

    def test_plain_text_escapes_angle_brackets(self):
        assert resolve_broadcast_text_to_html("a < b & c") == "a &lt; b &amp; c"

    def test_code_and_link_entities(self):
        entities = [
            MessageEntity(type="code", offset=0, length=3),
            MessageEntity(type="text_link", offset=4, length=4, url="https://t.me"),
        ]
        result = resolve_broadcast_text_to_html("foo link", entities)
        assert result == '<code>foo</code> <a href="https://t.me">link</a>'


class TestBuildBroadcastPreviewSnippet:
    """Regresión del incidente 2026-09-21: el corte a 500 chars partía una etiqueta."""

    def test_short_text_unchanged(self):
        from services.broadcast.text_format import build_broadcast_preview_snippet

        raw = "<b>PROMOS!</b> corto"
        assert build_broadcast_preview_snippet(raw) == raw

    def test_cut_right_after_lt_drops_dangling_tag(self):
        """El corte caía justo tras un '<' y el '...' del preview formaba '<...' (offset 850)."""
        from services.broadcast.text_format import build_broadcast_preview_snippet

        text = "x" * 499 + "<b>Promo VIP</b>"
        snippet = build_broadcast_preview_snippet(text)
        assert snippet == "x" * 499
        assert not snippet.endswith("<")
        assert "<..." not in snippet

    def test_open_tag_is_closed_after_cut(self):
        from services.broadcast.text_format import build_broadcast_preview_snippet

        snippet = build_broadcast_preview_snippet("<b>" + "y" * 600)
        assert snippet.startswith("<b>")
        assert snippet.endswith("</b>")

    def test_nested_open_tags_closed_in_order(self):
        from services.broadcast.text_format import build_broadcast_preview_snippet

        snippet = build_broadcast_preview_snippet("<b><i>" + "z" * 600)
        assert snippet.endswith("</i></b>")

    def test_cut_inside_attributes_retreats_to_tag_start(self):
        from services.broadcast.text_format import build_broadcast_preview_snippet

        text = "a" * 498 + '<a href="https://t.me/divan">link</a>'
        assert build_broadcast_preview_snippet(text) == "a" * 498


class TestStripBroadcastHtmlToPlainText:
    def test_removes_tags_and_unescapes(self):
        from services.broadcast.text_format import strip_broadcast_html_to_plain_text

        assert (
            strip_broadcast_html_to_plain_text("<b>Hola</b> &lt;mundo&gt; <i>x</i>")
            == "Hola <mundo> x"
        )


class TestMeasureTelegramTextLength:
    """Regresión del incidente 2026-11-15: caption de adjunto > 1024 rechazado por Telegram."""

    def test_empty_and_none(self):
        assert measure_telegram_text_length("") == 0
        assert measure_telegram_text_length(None) == 0

    def test_ignores_html_tags(self):
        assert measure_telegram_text_length("<b>Hola</b>") == 4
        assert measure_telegram_text_length("<b>Hola</b> &lt;mundo&gt;") == 12

    def test_counts_astral_emoji_as_two_utf16_units(self):
        assert measure_telegram_text_length("😀") == 2
        assert measure_telegram_text_length("a😀") == 3

    def test_counts_bmp_characters_as_one(self):
        assert measure_telegram_text_length("ñ") == 1


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
