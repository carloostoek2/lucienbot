---
phase: inline-package-creation
reviewed: 2026-06-21T12:00:00Z
depth: standard
files_reviewed: 5
files_reviewed_list:
  - handlers/package_handlers.py
  - handlers/store_admin_handlers.py
  - keyboards/callback_data.py
  - handlers/states/package_states.py
  - handlers/states/__init__.py
findings:
  critical: 2
  warning: 7
  info: 3
  total: 12
status: issues_found
---

# Inline Package Creation — Code Review Report

**Reviewed:** 2026-06-21T12:00:00Z
**Depth:** standard
**Files Reviewed:** 5
**Status:** issues_found

## Summary

Reviewed the inline package creation feature across 5 files. The feature allows admins to create a new package inline during product creation/editing without losing FSM context. The serialization/deserialization flow for `__return_context` is correctly implemented.

**Two BLOCKER issues found:**

1. The cancel/return flow is completely dead code — the global `cancel` handler in `common_handlers.py` is registered BEFORE `package_router` in `bot.py` and has no FSM state filter, so it intercepts ALL cancel callbacks. The package wizard's `cancel_package_wizard` handler that restores `__return_context` never executes.

2. The error recovery path in `confirm_create_package` sets the user to `selecting_package` state with no keyboard or UI — the user sees a text-only message with "Selecciónalo manualmente en la lista" but no package list is rendered.

Both issues make the inline return flow non-functional in critical paths.

---

## Critical Issues

### CR-01: Cancel/return flow is completely dead code — global cancel handler wins router priority

**File:** `handlers/package_handlers.py:865`
**File:** `handlers/common_handlers.py:237`
**File:** `bot.py:318`

**Issue:** The `cancel_package_wizard` handler at `package_handlers.py:865` registers on `PackageWizardStates + F.data == "cancel"`. Its purpose is to restore `__return_context` when the user cancels the inline package wizard and return to the product wizard.

However, a global cancel handler at `common_handlers.py:237` is registered on `F.data == "cancel"` with NO state filter. In `bot.py:318`, `common_router` is included BEFORE `package_router` (line 328). In aiogram 3, when multiple routers can match an update, the first registered router wins. Since the global handler has no FSM restriction, it matches ALL cancel callbacks unconditionally.

The package handler's `cancel_package_wizard` is NEVER called for any "cancel" callback. This means:

- When an admin is in the inline package wizard and presses "Cancelar", the global handler fires and shows a generic "Accion cancelada" message.
- The FSM state remains in `PackageWizardStates` (the global handler does not clear state).
- The `__return_context` is never restored.
- The admin is left in a stale FSM state with no recovery path from the UI.

The entire inline return-on-cancel feature is non-functional. This also affects the "Volver" flow from `ask_store_stock` and `ask_reward_stock` dialogs which use `callback_data="cancel"` — those cancel buttons also hit the global handler instead of the package wizard handler.

**Fix:** There are three possible approaches, ordered by robustness:

Option A (recommended): Use a namespaced callback data instead of the generic `"cancel"` string for package wizard cancel buttons. Create a `PackageWizardCancel` callback (or use `CancelPackageCallback`) so it does not collide with the global handler:

```python
# In keyboards/callback_data.py
class CancelPackageWizardCallback(CallbackData, prefix="cancel_pkg"):
    pass
```

Then update `cancel_keyboard()` usage in the package wizard to use this namespaced callback, and register the handler on it:

```python
@router.callback_query(PackageWizardStates, CancelPackageWizardCallback.filter())
async def cancel_package_wizard(callback: CallbackQuery, state: FSMContext):
    ...
```

Option B: Register `package_router` BEFORE `common_router` in bot.py. However, this changes the priority for ALL handlers in both routers, potentially breaking other cancel flows.

Option C: Add an FSM state check to the global cancel handler so it does not match when the user is in a meaningful FSM state:

```python
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        # Let specific handlers process this
        return
    ...
```

(This approach is fragile and not recommended.)

---

### CR-02: Error recovery path in confirm_create_package leaves user stuck in selecting_package state with no UI

**File:** `handlers/package_handlers.py:771-777`

**Issue:** When `_restore_product_context` fails after package creation, the error path restores FSM state to `ProductWizardStates.selecting_package` or `ProductEditStates.selecting_package`, but the Telegram message is updated with NO reply_markup. The message reads:

> "El paquete fue creado pero no pudo asignarse al producto automaticamente. Seleccionelo manualmente en la lista."

But no package list is shown — there are no inline buttons to click. The user is in a state that expects a `SelectPkgProductCallback` or `SelectPkgEditProductCallback` callback, but the UI has no such buttons. The old keyboard from the `PackageWizardStates.confirming` step is preserved by Telegram (because `edit_text` without `reply_markup` keeps the existing keyboard), but those buttons (`confirm_create_package` / `manage_packages`) are stale — pressing them leads to unexpected behavior:

- `confirm_create_package` does not match the current state (now `ProductWizardStates.selecting_package`, not `PackageWizardStates.confirming`), so the callback is silently ignored.
- `manage_packages` triggers the package management menu, leaving the user in `ProductWizardStates.selecting_package` with no way to return to the product wizard.

**Fix:** The error path should call `_wizard_prompt_package_selection` (or `build_edit_package_buttons`) to show the package selection list with a proper keyboard, exactly as the cancel path does:

```python
if return_context["source"] == "product_wizard":
    from handlers.store_admin_handlers import ProductWizardStates, _wizard_prompt_package_selection
    await state.set_state(ProductWizardStates.selecting_package)
    await _wizard_prompt_package_selection(callback, state)
else:
    from handlers.store_admin_handlers import ProductEditStates, build_edit_package_buttons
    product_id = return_context["data"]["edit_product_id"]
    await state.set_state(ProductEditStates.selecting_package)
    with get_service(StoreService) as store_service:
        packages = store_service.get_packages_for_product_edit(product_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=build_edit_package_buttons(product_id, packages)
    )
    await callback.message.edit_text(
        "🎩 Lucien:\n\nSelecciona el nuevo paquete:",
        reply_markup=keyboard,
    )
```

---

## Warnings

### WR-01: `SelectPkgProductCallback.product_id` semantically misnamed — holds package_id

**File:** `handlers/store_admin_handlers.py:793-794,879`

**Issue:** The `SelectPkgProductCallback` class defines a field `product_id`, but it is used to pass a **package** ID, not a product ID:

```python
# Line 794: building the button — passes pkg.id into product_id
callback_data=SelectPkgProductCallback(product_id=pkg.id).pack(),

# Line 879: reading the value
package_id = callback_data.product_id  # This is actually a package_id
```

The callback is for selecting a package during product creation, but the field is named after the product. This works because both IDs are integers, but it is extremely fragile. Future code reading `callback_data.product_id` will naturally assume it refers to a product. If anyone copies this pattern or adds a migration that changes ID types, this will silently break.

**Fix:** Rename the field in `SelectPkgProductCallback` to `package_id` and update all usages:

```python
class SelectPkgProductCallback(CallbackData, prefix="sel_pkg_prod"):
    package_id: int
```

Then update the builder at line 794 and the handler at line 879.

---

### WR-02: `confirm_create_package` calls two services — violates architecture rule

**File:** `handlers/package_handlers.py:728,840`

**Issue:** The `confirm_create_package` handler opens `get_service(PackageService)` at line 728 for package creation. When `__return_context` is present and source is `"product_edit"`, the `_restore_product_context` helper (called from within this `with` block) calls `get_service(StoreService)` at line 840 to update the product. This results in two service calls from a single handler, violating the "exactly 1 service" architecture rule.

**Fix:** Delegate the product update to the caller side, or refactor so that `create_package` on `PackageService` optionally accepts a `product_id` to update in a single transaction. Alternatively, move the package creation into a higher-level orchestrator that coordinates both services. At minimum, document the violation if it must remain.

---

### WR-03: `_restore_product_context` for product_edit commits DB update before Telegram message — silent data corruption risk

**File:** `handlers/package_handlers.py:838-842`

**Issue:** In the `"product_edit"` path of `_restore_product_context`, the product is updated in the database first:

```python
with get_service(StoreService) as store_service:
    store_service.update_product(product_id, package_id=package.id)  # DB commit
await target.message.edit_text(...)  # Telegram update
```

If `target.message.edit_text` fails (e.g., the original message was deleted, or flood control), the DB was already committed. The caller's except block then runs the error path, which shows "could not assign automatically" and reverts state to `selecting_package`. The user is told the assignment failed when it actually succeeded. If they manually re-select the same package, the product gets a redundant update (no harm), but if they select a different package, the old package assignment is overwritten.

**Fix:** Swap the order: update the Telegram message first, then commit the DB change. Or use a try/except around the Telegram update within `_restore_product_context` and only commit after success.

---

### WR-04: No `is_admin` guard on FSM sub-handlers (defense-in-depth)

**File:** `handlers/package_handlers.py:541,549,557,574,620,628,636,653,722,865`

**Issue:** Multiple handlers in the package creation FSM flow have no `is_admin` check:

- `store_stock_unlimited` (line 541)
- `store_stock_none` (line 549)
- `store_stock_limited` (line 557)
- `process_store_stock` (line 574)
- `reward_stock_unlimited` (line 620)
- `reward_stock_none` (line 628)
- `reward_stock_limited` (line 636)
- `process_reward_stock` (line 653)
- `confirm_create_package` (line 722)
- `cancel_package_wizard` (line 865)

These are protected by FSM scoping (only reachable if the user entered `PackageWizardStates` through `create_package_start`, which has `is_admin`). However, if there is any other code path that sets `PackageWizardStates` for a non-admin user, or if admin status is revoked while mid-wizard, these unprotected handlers become accessible to unauthorized users. The `cancel_package_wizard` handler is especially sensitive because it manipulates `__return_context` (restoring arbitrary state data and potentially re-entering another wizard flow).

**Fix:** Add an `is_admin` check to each handler. Pattern:

```python
if not is_admin(callback.from_user.id):
    await callback.answer("No autorizado", show_alert=True)
    await state.clear()
    return
```

---

### WR-05: Duplicate `import json` inside function body

**File:** `handlers/store_admin_handlers.py:862`

**Issue:** `import json` is already imported at module-level line 7. The redundant import inside `wizard_process_fulfillment_config` (line 862) is unnecessary and suggests the developer was unaware of the existing import. This can mask linter warnings and suggests the function was copied from a context where json was not yet imported.

**Fix:** Remove the inner `import json` at line 862.

---

### WR-06: Runtime imports from `store_admin_handlers` in `package_handlers.py` create fragile cross-module coupling

**File:** `handlers/package_handlers.py:766-770,889-890,897`

**Issue:** The file uses runtime (lazy) imports from `handlers.store_admin_handlers` in three places:

- Lines 766-770: `ProductWizardStates`, `ProductEditStates`
- Lines 889-890: `ProductWizardStates`, `_wizard_prompt_package_selection`
- Line 897: `ProductEditStates`, `build_edit_package_buttons`

While these avoid startup circular imports, they create fragile coupling: if any imported symbol is renamed or moved, the error surfaces at runtime (during admin use) rather than at import time. The function `_wizard_prompt_package_selection` is a private API (prefixed with `_`), making this coupling especially brittle.

This was flagged as MEDIUM in the design review and remains unresolved.

**Fix:** Extract the shared symbols (`_wizard_prompt_package_selection`, `build_edit_package_buttons`, and possibly the states) into a shared module (e.g., `handlers/store_shared.py`) that both handler files can import at module level without circular dependency.

---

### WR-07: `cancel_package_wizard` restore path missing `parse_mode="HTML"`

**File:** `handlers/package_handlers.py:906`

**Issue:** The cancel handler's product_edit restore path calls `callback.message.edit_text` without `parse_mode="HTML"`:

```python
await callback.message.edit_text(
    "🎩 Lucien:\n\nSelecciona el nuevo paquete:",
    reply_markup=keyboard,
)
```

While the current text does not contain HTML tags, this is inconsistent with every other message edit in the file which uses `parse_mode="HTML"`. If the text is later updated to include HTML formatting, it will render incorrectly.

**Fix:** Add `parse_mode="HTML"`.

---

## Info

### IN-01: Section header comments indented inside function bodies

**File:** `handlers/package_handlers.py:114,356,1030,1090,1364`

**Issue:** Section divider comments like `# ==================== LISTAR PAQUETES ====================` are indented inside the preceding function body, making it appear as though they are part of that function. For example:

```python
# Line 112: inside manage_packages_menu
        await callback.answer()
    
    # ==================== LISTAR PAQUETES ====================
    
# Line 118: actual next function starts here
@router.callback_query(PackageListCallback.filter(), lambda cb: is_admin(cb.from_user.id))
```

This does not affect execution but harms readability and makes the file harder to navigate. The same pattern occurs at lines 356 (inside `confirm_delete_package`), 1030 (inside `process_user_id_for_package`), 1090 (inside `view_package_files`), and 1364 (inside `confirm_update_package`).

**Fix:** Move section headers to column 0 (no indentation) to properly separate function boundaries.

---

### IN-02: Global cancel handler does not clear FSM state

**File:** `handlers/common_handlers.py:237-244`

**Issue:** The global `cancel_action` handler shows a generic "Accion cancelada" message but does not clear the FSM state. While this is a pre-existing issue (not introduced by this feature), it amplifies CR-01: when the global handler intercepts a cancel while the user is in `PackageWizardStates`, the user sees the cancel message but remains stuck in the package wizard state. Any subsequent message from that user could trigger an unexpected FSM handler response.

**Fix:** The global cancel handler should call `await state.clear()` to reset the FSM state:

```python
@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🎩 <b>Lucien:</b>\n\n<i>Acción cancelada. Diana aprecia la deliberacion...</i>",
        parse_mode="HTML",
    )
    await callback.answer("Accion cancelada")
```

---

### IN-03: `checklist` field not guarded as None in build_edit_package_buttons

**File:** `handlers/store_admin_handlers.py:321-356`

**Issue:** The `build_edit_package_buttons` function accepts `packages: list` and iterates over it without checking for `None`. While all callers pass a proper list (either from `get_packages_for_product_edit` or `get_available_packages_for_store`), a `None` value would raise `TypeError: 'NoneType' object is not iterable`. Adding a guard provides defensive programming.

**Fix:** Add early return for `None` or empty:

```python
def build_edit_package_buttons(product_id: int, packages: list | None) -> list[list[InlineKeyboardButton]]:
    buttons = []
    if not packages:
        return buttons
    ...
```

---

_Reviewed: 2026-06-21T12:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
