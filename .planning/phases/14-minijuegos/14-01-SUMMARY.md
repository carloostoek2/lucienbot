---
phase: 14
plan: 14-01
subsystem: minijuegos
key_files:
  - services/game_service.py
  - handlers/game_user_handlers.py
  - models/models.py (GameRecord, TransactionSource extension)
  - keyboards/inline_keyboards.py (game_* keyboards)
  - bot.py (game_user_router registration)
  - alembic/versions/c32861733e54_add_game_records_table_for_minijuegos.py
---

# Plan 14-01 Summary: Minijuegos Foundation

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Add GAME/TRIVIA to TransactionSource enum | 5f0878f | models/models.py |
| 2 | Create GameService with daily limits | 16da222 | services/game_service.py |
| 3 | Add GameRecord model | 16da222 | models/models.py |
| 4 | Add game keyboards | 722b9fc | keyboards/inline_keyboards.py |
| 5 | Create game_user_handlers | d70d1b5 | handlers/game_user_handlers.py |
| 6 | Register handlers in bot.py | 7de6729 | bot.py |
| 7 | Create Alembic migration | e5f85d3 | alembic/versions/c32861733e54_*.py |

## Implementation Details

### GameService (services/game_service.py)
- Daily limits: free (10 dice, 5 trivia) / VIP (20 dice, 10 trivia)
- VIP detection via VIPService.is_user_vip()
- Dice: roll 2 dice (1-6), win with "pairs" (both even) or "doubles" (equal)
- Trivia: load from docs/preguntas.json, 174 questions total
- Rewards: 1 besito (dice win), 2 besitos (trivia correct)

### GameRecord Model
- Tracks: user_id, game_type ('dice'/'trivia'), result, payout, played_at
- Query by date for daily limits

### Handlers
- game_menu: show menu with daily limits
- game_dice: show dice interface
- dice_play: process roll with voice of Lucien
- game_trivia: show random question
- trivia_answer: process answer

### Keyboard Integration
- main_menu_keyboard now includes "Minijuegos" button
- callback_data: game_menu → game_dice/game_trivia → dice_play

### Database
- Migration created: c32861733e54_add_game_records_table_for_minijuegos
- Table exists in dev DB (stamped)

## Deviation

- Migration auto-generated complex FK/index changes that were removed for simplicity
- Table existed from prior testing, stamped migration as applied

## Voice of Lucien

All messages use Lucien voice:
- Win: direct celebration ("¡GANASTE!", "¡CORRECTO!")
- Loss: subtle sarcasm ("Mejor suerte la próxima...", "Lucien observa...下次会有 más fortuna.")
- Free limit: VIP suggestion ("Los miembros VIP tienen el doble de oportunidades...")

## Verification Checklist

- [x] TransactionSource enum has GAME and TRIVIA
- [x] GameRecord model exists in models
- [x] GameService with daily limits functional
- [x] VIP detection works
- [x] Keyboards added to inline_keyboards.py
- [x] main_menu_keyboard has "Minijuegos" button
- [x] game_user_handlers.py with voice of Lucien
- [x] Handlers registered in bot.py
- [x] Migration applied (stamped)

## Commits

- 5f0878f: feat(models): add GAME and TRIVIA to TransactionSource enum
- 16da222: feat(game): add GameService and GameRecord model
- 722b9fc: feat(keyboards): add game menu keyboards and integrate in main menu
- d70d1b5: feat(handlers): add game_user_handlers for minijuegos
- 7de6729: feat(bot): register game_user_router in dispatcher
- e5f85d3: feat(db): add game_records migration for minijuegos