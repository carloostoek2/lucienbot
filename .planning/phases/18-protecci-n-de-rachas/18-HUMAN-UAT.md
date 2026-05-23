---
status: partial
phase: 18-protecci-n-de-rachas
source: [18-01-VERIFICATION.md]
started: 2026-05-23T03:10:00Z
updated: 2026-05-23T03:10:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Protection keyboard flow

expected: Play trivia (general/VIP/simple), fail a question with active promotion -> protection keyboard appears with cost, accept/decline buttons
result: [pending]

### 2. Risk mode retire/continue flow

expected: Reach a tier with streak -> retire/continue keyboard appears -> both paths produce correct state (retire preserves codes, continue sets risk mode)
result: [pending]

### 3. Timeout UX with 2-minute window

expected: Fail a question without enough besitos -> timeout message appears -> after 2 minutes, verify session expired -> codes cancelled
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
