---
phase: 09-polish-hardening
plan: '02'
subsystem: fsm-storage
tags: [redis, fsm, persistence, aiogram]
dependency_graph:
  requires: []
  provides:
    - "FSM state persists across bot restarts via RedisStorage when REDIS_URL is set"
  affects:
    - bot.py
    - requirements.txt
tech_stack:
  added:
    - "redis==5.0.1 (async Redis client)"
    - "aiogram.fsm.storage.redis (RedisStorage, DefaultKeyBuilder)"
  patterns:
    - "Factory pattern for storage instantiation with graceful fallback"
key_files:
  created: []
  modified:
    - bot.py
    - requirements.txt
decisions: []
metrics:
  duration: "~3 minutes"
  completed_date: "2026-03-31"
---

# Phase 09 Plan 02: RedisStorage FSM Persistence Summary

## One-liner

RedisStorage FSM with graceful MemoryStorage fallback via `create_storage()` factory.

## Completed Tasks

### Task 1: Add create_storage factory function to bot.py

**Commit:** `32036a7`

Modified `bot.py` to replace hardcoded `MemoryStorage()` with a factory function:

- Added imports: `os`, `timedelta`, `RedisStorage`, `DefaultKeyBuilder`, `Redis`
- Added `create_storage()` factory after logger setup (line 60)
- Replaced `storage = MemoryStorage()` with `storage = create_storage()` in `main()` (line 211)
- Factory uses `RedisStorage` when `REDIS_URL` env var is set
- Falls back to `MemoryStorage` with logged warning when `REDIS_URL` not set
- Uses aiogram 3.24.0 API: `RedisStorage(redis=Redis.from_url(...), ...)` — NOT `url=`

### Task 2: Verify requirements.txt has redis

**Commit:** `e2000a1`

Added `redis==5.0.1` to `requirements.txt` (was missing despite being listed in plan).

## Deviations from Plan

None — plan executed exactly as written.

## Acceptance Criteria Checklist

- [x] `bot.py` contains `def create_storage():`
- [x] `bot.py` contains `redis_url = os.getenv("REDIS_URL")`
- [x] `bot.py` contains `RedisStorage(` (not `RedisStorage(url=...)`)
- [x] `bot.py` contains `redis_client = Redis.from_url(redis_url)`
- [x] `bot.py` contains `DefaultKeyBuilder(with_bot_id=True)`
- [x] `bot.py` contains `return MemoryStorage()` as fallback
- [x] `bot.py` contains `storage = create_storage()` (not hardcoded)
- [x] `bot.py` imports `from redis.asyncio import Redis`
- [x] `bot.py` imports `from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder`
- [x] `bot.py` imports `import os` and `from datetime import timedelta`
- [x] `requirements.txt` contains `redis==5.0.1`

## Commits

| Commit | Message |
|--------|---------|
| `32036a7` | feat(09-02): add create_storage() factory with RedisStorage fallback |
| `e2000a1` | chore(09-02): add redis==5.0.1 for RedisStorage FSM persistence |

## Self-Check

- [x] bot.py contains `def create_storage`
- [x] bot.py contains `create_storage()` call in main()
- [x] No broken `RedisStorage(url=...)` usage
- [x] requirements.txt contains redis==5.0.1
- [x] Both commits verified in git log

## Self-Check: PASSED
