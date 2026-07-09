"""Unit tests for unified broadcast channel reaction markup builders."""

from unittest.mock import MagicMock

import pytest

from keyboards.callback_data import ReactionCallback


def _markup_structure(markup):
    """Normalize markup to comparable structure (exclude count text)."""
    return [
        [
            {
                "callback_data": btn.callback_data,
                "url": getattr(btn, "url", None),
            }
            for btn in row
        ]
        for row in markup.inline_keyboard
    ]


@pytest.mark.unit
class TestBroadcastChannelMarkup:
    """Tests para build_channel_reaction_markup y helpers puros."""

    def test_build_broadcast_send_markup_reactions_only(self):
        """Solo emojis → una fila con ReactionCallbacks, sin URL."""
        from keyboards.broadcast_channel_markup import build_broadcast_send_markup

        mock_emoji = MagicMock(id=1, emoji="💋")

        def get_emoji(eid):
            return mock_emoji if eid == 1 else None

        markup = build_broadcast_send_markup(
            broadcast_id=42,
            selected_emoji_ids=[1],
            extra_button=None,
            get_emoji=get_emoji,
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 1
        btn = markup.inline_keyboard[0][0]
        assert btn.text == "💋"
        assert btn.callback_data.startswith("react:")

    def test_build_broadcast_send_markup_extra_only(self):
        """Sin emojis, con extra → fila única con url (sin callback)."""
        from keyboards.broadcast_channel_markup import build_broadcast_send_markup

        class FakeBtn:
            label = "🔗 Más"
            url = "https://t.me/kinky"

        markup = build_broadcast_send_markup(
            broadcast_id=42,
            selected_emoji_ids=[],
            extra_button=FakeBtn(),
            get_emoji=lambda eid: None,
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 1
        btn = markup.inline_keyboard[0][0]
        assert btn.text == "🔗 Más"
        assert btn.url == "https://t.me/kinky"
        assert getattr(btn, "callback_data", None) in (None, "")

    def test_build_broadcast_send_markup_combined(self):
        """Emojis + extra → 2 filas: reacciones (callbacks) + url."""
        from keyboards.broadcast_channel_markup import build_broadcast_send_markup

        mock_emoji = MagicMock(id=9, emoji="❤️")

        def get_emoji(eid):
            return mock_emoji if eid == 9 else None

        class FakeBtn:
            label = "📎 Ver"
            url = "https://t.me/extra"

        markup = build_broadcast_send_markup(
            broadcast_id=99,
            selected_emoji_ids=[9],
            extra_button=FakeBtn(),
            get_emoji=get_emoji,
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 2
        assert markup.inline_keyboard[0][0].callback_data.startswith("react:")
        assert markup.inline_keyboard[1][0].url == "https://t.me/extra"

    def test_build_broadcast_send_markup_none(self):
        """Sin nada → None."""
        from keyboards.broadcast_channel_markup import build_broadcast_send_markup

        markup = build_broadcast_send_markup(
            broadcast_id=1,
            selected_emoji_ids=[],
            extra_button=None,
            get_emoji=lambda eid: None,
        )
        assert markup is None

    def test_build_broadcast_send_markup_chunks_nine_emojis(self):
        """Más de 8 emojis → varias filas (límite Telegram)."""
        from keyboards.broadcast_channel_markup import build_broadcast_send_markup

        emojis = {i: MagicMock(id=i, emoji=f"E{i}") for i in range(1, 10)}
        markup = build_broadcast_send_markup(
            broadcast_id=19,
            selected_emoji_ids=list(range(1, 10)),
            extra_button=None,
            get_emoji=lambda eid: emojis.get(eid),
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 2
        assert len(markup.inline_keyboard[0]) == 8
        assert len(markup.inline_keyboard[1]) == 1

    def test_chunk_reaction_buttons_pure(self):
        from aiogram.types import InlineKeyboardButton

        from keyboards.broadcast_channel_markup import chunk_reaction_buttons

        buttons = [InlineKeyboardButton(text=str(i), callback_data=f"x:{i}") for i in range(10)]
        rows = chunk_reaction_buttons(buttons, max_per_row=8)
        assert len(rows) == 2
        assert len(rows[0]) == 8
        assert len(rows[1]) == 2

    def test_build_send_reaction_markup_uses_reaction_callback(self):
        """Helper de envío genera callback_data compatible con handle_reaction."""
        from keyboards.broadcast_channel_markup import build_send_reaction_markup

        emoji = MagicMock()
        emoji.id = 3
        emoji.emoji = "💋"
        markup = build_send_reaction_markup(99, [3], lambda _eid: emoji)
        button = markup.inline_keyboard[0][0]
        unpacked = ReactionCallback.unpack(button.callback_data)
        assert unpacked.broadcast_id == 99
        assert unpacked.emoji_id == 3

    def test_refresh_mode_count_zero_shows_emoji_only(self):
        """Refresh: count=0 → text is emoji only."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        markup = build_channel_reaction_markup(
            42,
            [(1, "💋")],
            emoji_counts={1: 0},
        )
        assert markup.inline_keyboard[0][0].text == "💋"

    def test_refresh_mode_count_positive_shows_emoji_and_count(self):
        """Refresh: count>0 → text is 'emoji count'."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        markup = build_channel_reaction_markup(
            42,
            [(1, "💋")],
            emoji_counts={1: 3},
        )
        assert markup.inline_keyboard[0][0].text == "💋 3"

    def test_refresh_preserves_extra_button_url_row(self):
        """Refresh con extra_button → 2 filas: reacciones + url."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        class FakeBtn:
            label = "🔗 Link"
            url = "https://t.me/foo"

        markup = build_channel_reaction_markup(
            99,
            [(10, "🔥")],
            emoji_counts={10: 0},
            extra_button=FakeBtn(),
        )
        assert markup is not None
        assert len(markup.inline_keyboard) == 2
        url_btn = markup.inline_keyboard[1][0]
        assert url_btn.url == "https://t.me/foo"
        assert url_btn.text == "🔗 Link"
        assert markup.inline_keyboard[0][0].callback_data.startswith("react:")

    def test_calculate_emoji_counts_from_reactions(self):
        from keyboards.broadcast_channel_markup import calculate_emoji_counts_from_reactions

        r1 = MagicMock()
        r1.reaction_emoji = MagicMock(id=1)
        r2 = MagicMock()
        r2.reaction_emoji = MagicMock(id=1)
        r3 = MagicMock()
        r3.reaction_emoji = MagicMock(id=2)
        counts = calculate_emoji_counts_from_reactions([r1, r2, r3])
        assert counts == {1: 2, 2: 1}

    def test_send_refresh_structure_parity_reactions_only(self):
        """Send vs refresh (zero counts): identical structure and button text."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        bid = 42
        entries = [(1, "💋"), (2, "❤️")]
        send = build_channel_reaction_markup(bid, entries, emoji_counts=None)
        refresh_zero = build_channel_reaction_markup(bid, entries, emoji_counts={1: 0, 2: 0})
        assert _markup_structure(send) == _markup_structure(refresh_zero)
        for row_send, row_refresh in zip(
            send.inline_keyboard, refresh_zero.inline_keyboard, strict=True
        ):
            for btn_send, btn_refresh in zip(row_send, row_refresh, strict=True):
                assert btn_send.text == btn_refresh.text

    def test_send_refresh_structure_parity_with_extra_button(self):
        """Send vs refresh with extra URL row: structure and text parity at zero counts."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        class FakeBtn:
            label = "🔗 Más"
            url = "https://t.me/kinky"

        bid = 99
        entries = [(9, "❤️")]
        send = build_channel_reaction_markup(
            bid, entries, emoji_counts=None, extra_button=FakeBtn()
        )
        refresh_zero = build_channel_reaction_markup(
            bid, entries, emoji_counts={9: 0}, extra_button=FakeBtn()
        )
        assert _markup_structure(send) == _markup_structure(refresh_zero)
        assert send.inline_keyboard[0][0].text == refresh_zero.inline_keyboard[0][0].text
        assert send.inline_keyboard[1][0].text == refresh_zero.inline_keyboard[1][0].text

    def test_send_refresh_structure_parity_nine_emoji_chunking(self):
        """8+1 emoji chunking: send and refresh-zero share row layout and callbacks."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        bid = 19
        entries = [(i, f"E{i}") for i in range(1, 10)]
        zero_counts = {i: 0 for i, _ in entries}
        send = build_channel_reaction_markup(bid, entries, emoji_counts=None)
        refresh_zero = build_channel_reaction_markup(bid, entries, emoji_counts=zero_counts)
        assert _markup_structure(send) == _markup_structure(refresh_zero)
        assert len(send.inline_keyboard) == 2
        assert len(send.inline_keyboard[0]) == 8
        assert len(send.inline_keyboard[1]) == 1

    def test_refresh_with_positive_count_structure_same_text_differs(self):
        """Positive count: structure matches send; only reaction button text differs."""
        from keyboards.broadcast_channel_markup import build_channel_reaction_markup

        bid = 42
        entries = [(1, "💋")]
        send = build_channel_reaction_markup(bid, entries, emoji_counts=None)
        refresh_counted = build_channel_reaction_markup(bid, entries, emoji_counts={1: 3})
        assert _markup_structure(send) == _markup_structure(refresh_counted)
        assert send.inline_keyboard[0][0].text == "💋"
        assert refresh_counted.inline_keyboard[0][0].text == "💋 3"
