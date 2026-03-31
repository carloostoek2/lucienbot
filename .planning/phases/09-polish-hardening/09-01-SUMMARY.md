---
phase: 09-polish-hardening
plan: "01"
subsystem: Security / Infrastructure
tags: [rate-limiting, middleware, aiolimiter, aiogram-3.24]
dependency_graph:
  requires: []
  provides:
    - ThrottlingMiddleware (handlers/rate_limit_middleware.py)
    - RateLimitConfig (config/settings.py)
  affects:
    - bot.py (middleware registration)
    - requirements.txt (aiolimiter, aiogram fix)
tech_stack:
  added:
    - aiolimiter==1.2.1
    - APScheduler==3.10.4
    - redis==5.0.1
  patterns:
    - aiogram BaseMiddleware for global rate limiting
    - Sliding window via AsyncLimiter
    - Admin bypass pattern
key_files:
  created:
    - handlers/rate_limit_middleware.py (63 lines)
  modified:
    - config/settings.py (+11 lines: RateLimitConfig dataclass)
    - bot.py (+6 lines: middleware registration)
    - requirements.txt (+7 lines: aiolimiter, APScheduler, aiogram fix)
decisions:
  - "Per-user sliding window rate limiting: 5 requests / 10 seconds via aiolimiter AsyncLimiter"
  - "Admin bypass: bot_config.ADMIN_IDS checked before limiter acquisition"
  - "aiogram 3.24.0 used as canonical version (was 3.4.1 in requirements)"
metrics:
  duration_seconds: ~45
  completed_date: "2026-03-31"
  tasks_completed: 4
  files_created: 1
  files_modified: 3
---

# Phase 09 Plan 01: Rate Limiting Middleware Summary

## One-liner

Per-user sliding-window rate limiting with aiolimiter and admin bypass, protecting all user-facing handlers globally.

## What Was Built

**Task 1 - RateLimitConfig in settings.py**
- Added `RateLimitConfig` dataclass with `RATE_LIMIT_RATE=5`, `RATE_LIMIT_PERIOD=10.0`, `ADMIN_BYPASS=True`
- Instantiated as `rate_limit_config` global

**Task 2 - ThrottlingMiddleware in handlers/rate_limit_middleware.py**
- Created `ThrottlingMiddleware(BaseMiddleware)` using `aiolimiter.AsyncLimiter`
- Extracts `user_id` from `data.get("event_from_user")`
- Admin bypass via `user_id in bot_config.ADMIN_IDS`
- Lucien-themed throttling reply on limit exceeded (`show_alert=True`)

**Task 3 - Middleware registered in bot.py**
- `dp.message.middleware(ThrottlingMiddleware())` and `dp.callback_query.middleware(ThrottlingMiddleware())`
- Placed after dispatcher creation and before any router registration

**Task 4 - requirements.txt updated**
- `aiogram==3.24.0` (fixed from 3.4.1)
- `aiolimiter==1.2.1`
- `APScheduler==3.10.4`
- `redis==5.0.1` (already present)

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 | c339ada | feat(09-01): add RateLimitConfig to settings |
| 2 | 3f07b6b | feat(09-01): add ThrottlingMiddleware for per-user rate limiting |
| 3 | e5eb4c6 | feat(09-01): register ThrottlingMiddleware globally on dp |
| 4 | 4fa6280 | chore(09-01): update requirements.txt for Phase 9 |

## Success Criteria Met

- [x] Non-admin users are throttled after 5 requests in 10 seconds
- [x] Custodios (admins) bypass rate limiting entirely
- [x] Throttling returns a Lucien-themed response without crashing the handler chain
- [x] ThrottlingMiddleware applied globally to both message and callback_query routers

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check

- [x] handlers/rate_limit_middleware.py exists with correct content
- [x] config/settings.py contains RATE_LIMIT_RATE=5, RATE_LIMIT_PERIOD=10.0, rate_limit_config
- [x] bot.py registers ThrottlingMiddleware on both message and callback_query
- [x] requirements.txt contains aiolimiter, APScheduler, redis, aiogram==3.24.0
- [x] All 4 commits verified in git log

## Self-Check: PASSED
