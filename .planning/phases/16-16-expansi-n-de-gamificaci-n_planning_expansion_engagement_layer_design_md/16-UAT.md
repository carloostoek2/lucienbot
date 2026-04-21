---
status: testing
phase: 16-16-expansi-n-de-gamificaci-n_planning_expansion_engagement_layer_design-md
source: 16-01a-SUMMARY.md, 16-02a-SUMMARY.md, 16-02b-SUMMARY.md, 16-03b-SUMMARY.md, 16-04a-SUMMARY.md, 16-04b-SUMMARY.md
started: 2026-04-16T22:50:00Z
updated: 2026-04-17T01:45:00Z
---

## Current Test

number: 7
name: Susurros de Diana — Daily Claim
expected: |
  User can claim one free whisper per day from the pool. VIP users see option to claim an additional VIP whisper.
awaiting: user response

## Tests

### 1. Ritmo Diario — Daily Streak Claim
expected: User can claim their daily ritual (Ritmo Diario) and see streak counter increment. If VIP, sees recovery option when streak is at risk.
result: issue
reported: "Los botones de ritmo diario y susurros no funcionan, en la consola sale marcados como not handled"
severity: major

### 2. Ritmo Diario — Passive Income Calculation
expected: When user claims after being away, receives passive besitos based on away time (8h cap for free, 24h for VIP) plus streak multiplier.
result: pass

### 3. Mission Templates — Admin CRUD
expected: Admin can create, view, update, and delete mission templates via admin menu. Templates include type, target value, reward, weight, VIP exclusivity.
result: issue
reported: "no hay boton de templates"
severity: major

### 4. Daily Mission Generation — Automatic
expected: System automatically generates daily missions at midnight from active templates. Previous day's daily missions are deactivated.
result: pass

### 5. Senderos del Espejo — Path Display
expected: User sees available story paths in main menu. Each path shows name, description, and VIP lock status if applicable.
result: pass

### 6. Senderos del Espejo — Path Progression
expected: User can start a path and advance through nodes by selecting choices. Completion triggers reward delivery.
result: pass

### 7. Susurros de Diana — Daily Claim
expected: User can claim one free whisper per day from the pool. VIP users see option to claim an additional VIP whisper.
result: [pending]

### 8. Susurros de Diana — Admin Pool Management
expected: Admin can view configured whisper pools and their current status (active/inactive, item count).
result: [pending]

### 9. Whisper Reward Pool — Creation and Items
expected: Admin can create whisper pools with specific codes and add/remove reward items with weighted selection.
result: [pending]

### 10. Whisper Claims — Daily Limit Enforcement
expected: System prevents user from claiming more than allocated whispers per day (1 free, 1 VIP). Shows appropriate feedback.
result: [pending]

## Summary

total: 10
passed: 4
issues: 2
pending: 4
skipped: 0

## Gaps

- truth: "Ritmo Diario button works and shows streak claim flow"
  status: failed
  reason: "User reported: Los botones de ritmo diario y susurros no funcionan, en la consola sale marcados como not handled"
  severity: major
  test: 1
  root_cause: "engagement_user_router and engagement_admin_router were imported but NOT registered in dp.include_router() in bot.py"
  artifacts:
    - path: "bot.py"
      issue: "Missing dp.include_router(engagement_user_router) and dp.include_router(engagement_admin_router)"
  missing:
    - "Add dp.include_router(engagement_user_router) after backpack_router"
    - "Add dp.include_router(engagement_admin_router) after engagement_user_router"
  debug_session: ""

- truth: "Ritmo Diario displays streak status without errors"
  status: fixed
  reason: "TypeError fixed by adding timezone normalization in can_claim() method"
  severity: blocker
  test: 2
  root_cause: "datetime.now(timezone.utc) is timezone-aware but claimed_at from DB is stored as naive"
  artifacts:
    - path: "services/daily_gift_service.py"
      issue: "Line 113: time_since_last = now - last_claim.claimed_at fails when mixing aware and naive datetimes"
      fix_applied: "Added timezone normalization before subtraction"
  missing: []
  debug_session: ""

- truth: "Mission Templates button appears in admin menu"
  status: failed
  reason: "User reported: no hay boton de templates"
  severity: major
  test: 3
  root_cause: "admin_menu_keyboard in inline_keyboards.py does not include button for admin_mission_templates"
  artifacts:
    - path: "keyboards/inline_keyboards.py"
      issue: "Missing button for mission templates in admin menu"
  missing:
    - "Add button for admin_mission_templates in admin_menu_keyboard"
  debug_session: ""