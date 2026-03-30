# SYSTEM RULES (NON-NEGOTIABLE)

## 1. Handler Rules

Cada handler debe:
- llamar a UN service
- no contener lógica

SI un handler tiene lógica:
→ está mal

---

## 2. Service Rules

Cada service:
- es dueño de un dominio
- centraliza lógica

PROHIBIDO:
- lógica duplicada en múltiples services

---

## 3. Function Rules

- máximo 50 líneas
- una sola responsabilidad

---

## 4. Anti-Patterns (PROHIBIDOS)

- lógica en handlers
- acceso directo a DB fuera de models
- duplicación de lógica
- funciones genéricas tipo:
  - process_data
  - handle_logic

---

## 5. Naming

Funciones:
- verbo + contexto + resultado

Ejemplo:
- calculate_user_besitos_from_reactions

---

## 6. Logging

Cada acción importante debe loguear:

- módulo
- acción
- user_id
- resultado

---

## 7. LLM Rules (CRÍTICO)

Cuando un LLM modifica código:

DEBE:
- leer architecture.md
- respetar domain boundaries

NO DEBE:
- crear nuevos archivos sin razón clara
- mover lógica entre capas
- duplicar lógica existente

---

## 8. Refactoring Rules

Solo permitido si:
- reduce complejidad
- elimina duplicación

---

## 9. Tests

Cada service debe tener:
- al menos 1 test crítico
