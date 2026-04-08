Implement an Admin User Simulation System for role-based behavior testing inside the Telegram bot.

OBJECTIVE

Allow admin users to simulate different user roles (e.g., FREE, VIP) without modifying real user data or triggering permanent side effects.

This is NOT a role mutation system.
It is a temporary context override system.

---

CORE PRINCIPLE

Never modify the actual user role in the database.

All simulations must be handled via a runtime override layer.

---

REQUIREMENTS

1. Admin Override Store

Implement a storage mechanism (in-memory is acceptable for now) that maps:

admin_user_id → simulation context

Example:

{
admin_id: {
"role": "vip" | "free" | None,
"activated_at": timestamp
}
}

---

2. Context Resolution Layer

Create a centralized function:

resolve_user_context(user_id, real_user_data)

This function must:

- Check if the user has an active override
- If yes → return simulated role
- If not → return real role

This function becomes the single source of truth for user state.

---

3. Middleware Integration

Integrate the context resolution into the request lifecycle:

- Extend existing middleware (e.g., auth or context middleware)
- Inject resolved context into handler scope (e.g., "context.user_role")

All downstream logic must use this resolved context.

---

4. Refactor Role Checks

Replace direct checks like:

user.is_vip

with:

context.is_vip

This must be applied consistently across:

- handlers
- services
- business logic

---

5. Admin Controls (Bot UI)

Add admin-only commands or panel options:

- Switch to FREE mode
- Switch to VIP mode
- Reset to REAL mode

Display current mode clearly:

"⚠️ Simulation mode: VIP"

---

6. Safety Restrictions

When simulation mode is active:

- Prevent permanent state changes:
  - payments
  - balance updates
  - reward grants
- Optionally log blocked actions for visibility

---

7. Scope and Isolation

- Overrides apply ONLY to the admin who activated them
- Must not affect other users
- Must not persist across restarts (unless explicitly designed later)

---

8. Optional Enhancements

- Add expiration (e.g., auto-reset after 30 minutes)
- Extend simulation to additional fields:
  - balance
  - subscription status

---

NON-GOALS

- Do not modify database schema
- Do not introduce external dependencies
- Do not implement full testing framework

---

EXPECTED OUTCOME

Admins can safely simulate user roles and test flows without:

- altering real data
- triggering unintended side effects
- requiring manual DB manipulation

---

DESIGN PRINCIPLE

This system must behave like a read-time override layer, not a write-time mutation.

All real data must remain untouched.




🔍 Lo que tienes que vigilar mientras implementas
No avances rápido. Valida esto:
1. 🔴 Punto único de verdad
Debes poder responder sin dudar:
“¿De dónde sale el rol que usa el sistema?”
Si la respuesta no es: → resolve_user_context()
entonces ya perdiste consistencia.
2. 🔴 Propagación real del contexto
No basta con calcularlo.
Debes asegurarte que:
handlers lo reciben
services lo reciben
middlewares lo respetan
Si en algún punto vuelves a consultar DB directamente: → rompiste el sistema
