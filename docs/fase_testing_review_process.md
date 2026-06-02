# Metodología de Revisión de Testing por Fase

**Versión:** 1.0  
**Fecha:** Junio 2026  
**Propósito:** Definir un proceso repetible, objetivo y trazable para revisar la cobertura de testing de cada fase de desarrollo del proyecto Lucien Bot.

---

## 1. Objetivo

Establecer un marco de trabajo consistente para responder, fase por fase:

- ¿Qué prometió esta fase según su documentación oficial?
- ¿Qué comportamiento **deseado** (contrato) debería tener el sistema según la arquitectura, las reglas del proyecto y el análisis realizado?
- ¿Qué comportamientos importantes **no** están cubiertos por tests que validen ese contrato (o están cubiertos de forma frágil)?
- ¿Qué tests específicos se recomiendan crear o fortalecer para proteger el comportamiento correcto?

**Filosofía central**: La documentación y los tests se escriben contra el **comportamiento deseado**, no contra la implementación actual (que puede contener deuda técnica, excepciones arquitecturales o patrones antiguos).

Cuando un test falla, el primer paso **no** es asumir que hay que cambiar el código de producción. Se debe investigar la causa raíz para determinar:
- Si el componente realmente está fallando, o
- Si el test está escrito de forma "rara" pero el comportamiento actual es funcionalmente correcto.

Solo después de ese análisis se decide si conviene refactorizar.

El objetivo final es reducir la deuda de testing de manera ordenada y prudente, priorizando el riesgo real de "sacositas".

---

## 2. Alcance

Esta metodología aplica a todas las fases documentadas en `.planning/phases/`.

Se recomienda seguir un orden **cronológico** (desde las fases más tempranas) para evitar dejar huecos y mantener trazabilidad histórica.

---

## 3. Fuentes de Información (Obligatorias)

Para cada fase se deben consultar **al menos** las siguientes fuentes:

| Fuente | Ubicación típica | Qué buscar |
|--------|------------------|------------|
| Documentación oficial de la fase | `.planning/phases/<fase>/` (`PLAN.md`, `CONTEXT.md`, `SUMMARY.md`, `VERIFICATION.md`, `RESEARCH.md`) | Objetivos, requisitos, entregables prometidos, criterios de éxito |
| Código implementado | `services/`, `handlers/`, `models/` relacionados con la fase | Funcionalidad real existente |
| Tests existentes | `tests/unit/`, `tests/integration/`, `tests/handlers/` | Qué se está probando realmente hoy |
| `refactor_testing.md` y `fases_refactor_testing.md` | Raíz del proyecto | Contexto previo de deuda de testing relacionado con la fase |
| Commits y GSD logs | Git + `.planning/quick/` (si aplica) | Trabajo previo de testing en esa área |

---

## 4. Flujo de Revisión por Fase (Proceso Paso a Paso)

Se recomienda seguir este orden para cada fase:

### Paso 1: Entender la promesa de la fase
- Leer `PLAN.md` + `CONTEXT.md` + `SUMMARY.md`.
- Extraer:
  - Objetivo principal de la fase.
  - Funcionalidades/entregables clave.
  - Criterios de éxito explícitos o implícitos.

### Paso 2: Mapear la funcionalidad actual
- Identificar los servicios, handlers y modelos principales que implementan lo prometido.
- Listar los flujos de negocio más importantes (happy path + casos de error relevantes).

### Paso 3: Inventario de tests existentes
- Buscar tests (unit, integration, e2e, handlers) que ejerciten los componentes de la fase.
- Clasificarlos en:
  - Tests determinísticos (buenos)
  - Tests dependientes de datos preexistentes (frágiles)
  - Tests que usan mocks pesados vs tests que validan contratos reales

### Paso 4: Análisis de brechas
Evaluar contra los siguientes criterios (priorizados):

- **Cobertura de contratos deseados**: ¿Existen tests (y documentación) que validen explícitamente el comportamiento que *debería* tener el sistema según arquitectura y reglas, o solo se prueba la implementación actual?
- **Uso del patrón correcto**: ¿Usan SQLite en archivo + TestSession cuando hay múltiples commits internos?
- **Idempotencia y atomicidad**: ¿Están cubiertos escenarios de fallo parcial?
- **Invariantes de negocio**: ¿Hay tests que validen propiedades que siempre deben cumplirse?
- **Casos de error y edge cases**: ¿Solo happy paths o también fallos?
- **Integración cross-service**: ¿Se prueban interacciones entre dominios?

**Importante**: Durante este paso se debe contrastar lo encontrado con el "comportamiento deseado" definido en la documentación y en los análisis de agentes (no solo con lo que el código hace hoy).

### Paso 5: Recomendaciones
Para cada brecha importante se debe definir:

- **Tipo de recomendación**:
  - Nuevo test unitario
  - Nuevo test de integración (siguiendo patrón SQLite+TestSession)
  - Fortalecimiento de test existente
  - Extracción de lógica a servicio para facilitar testing
- **Prioridad** (Alta / Media / Baja)
- **Esfuerzo estimado** (bajo / medio / alto)
- **Riesgo mitigado** (qué "sacosita" se previene)

### Paso 6: Registro
- Actualizar `fases_refactor_testing.md` (o documento equivalente) con:
  - Resumen de la fase
  - Tabla de brechas encontradas
  - Recomendaciones priorizadas
  - Estado (Pendiente / En progreso / Completado)

---

## 5. Template de Salida por Fase (Recomendado)

Se sugiere generar (o actualizar) por cada fase revisada una sección con esta estructura:

```markdown
### Fase X: Nombre de la Fase

**Promesa principal de la fase:**
- ...

**Componentes principales involucrados:**
- Services: ...
- Handlers: ...
- Models: ...

**Tests existentes relevantes:**
- ...

**Brechas identificadas:**

| # | Brecha | Severidad | Tipo de test recomendado | Prioridad | Notas |
|---|--------|-----------|---------------------------|-----------|-------|
| 1 | ... | Alta | Integración (patrón SQLite) | Alta | ... |

**Recomendaciones:**
- ...
```

---

## 6. Criterios de Calidad para los Tests Recomendados

Todo nuevo test que se proponga debe aspirar a:

- Ser **determinístico** (no depender de datos que ya existan en la BD de test).
- Usar el **patrón SQLite en archivo + TestSession** cuando haya múltiples commits internos de servicios.
- Validar **comportamiento deseado** (el contrato que el sistema debería cumplir según arquitectura y reglas del proyecto), aunque la implementación actual sea diferente.
- Preferir tests de **contrato** sobre tests que solo validen "que no explote".
- Incluir al menos un caso de **error o edge case** relevante.
- Ser escrito de forma que, si falla, permita una investigación clara de causa raíz (en lugar de ser frágil o ambiguo).

---

## 7. Herramientas y Convenciones

### Uso de Agentes Especializados (recomendado)

Se debe aprovechar el sistema de subagentes de la CLI de la siguiente forma:

- **Exploración profunda de dominio**: Usar un agente de tipo `explore` para mapear la arquitectura actual, flujos clave, y puntos de dolor (IDs, patrones de instanciación, bypasses, violaciones de reglas, documentación obsoleta).
- **Análisis de impacto previo**: **Siempre** usar el agente `impact-analyzer` **antes** de planificar o ejecutar cualquier cambio en servicios, handlers o modelos. Este agente genera un mapa de consumidores, riesgos de "cambié A y se rompió B", y lista de tests obligatorios.
- **Diseño de refactor o plan**: Usar agentes de tipo `plan` o `general-purpose` para proponer scopes quirúrgicos de bajo riesgo.

Los agentes pueden correr en background mientras se continúa el trabajo. Sus resultados se consultan con `get_command_or_subagent_output`.

### Filosofía de Testing por Contrato (no por implementación actual)

- La documentación y los tests se escriben contra el **comportamiento deseado** ("lo que el sistema debería hacer" según arquitectura, reglas del proyecto y análisis de agentes), no contra lo que el código ejecuta hoy.
- Cuando un test falla:
  1. Investigar primero la causa raíz.
  2. Determinar si el componente realmente está fallando o si el test está escrito de forma "rara" pero el comportamiento de producción es correcto.
  3. Solo después de ese análisis decidir si conviene refactorizar.

Esto evita escribir tests frágiles que protejan deuda técnica o que haya que reescribir tras una limpieza.

### Patrones y Aspectos Clave a Buscar Durante la Exploración

Al analizar el código de una fase se debe prestar especial atención a:

- **Manejo de IDs duales** (ej: DB PK vs ID externo de Telegram) — una de las fuentes más comunes de bugs silenciosos y deuda.
- **Patrones de instanciación de servicios** (viejo `Service() + try/finally` vs moderno `with get_service(...)`).
- **Bypasses directos a DB o cross-domain** (queries crudas desde otros servicios, mutaciones directas en scheduler, etc.).
- **Documentación obsoleta** (especialmente archivos CLAUDE.md por dominio).
- **Violaciones de reglas de handlers** ("exactamente 1 service", sin lógica de negocio, sin DB).
- **Integración con Scheduler** (jobs que usan SessionLocal directo, bypass de métodos del servicio).
- **Uso consistente del patrón de tests robustos** (SQLite en archivo + TestSession independiente para flujos con múltiples commits internos).

### Inicio de Bajo Riesgo

Se recomienda comenzar cualquier revisión de fase con:
1. Actualización de documentación (CLAUDE.md + docstrings) que describa el contrato deseado.
2. Escritura de uno o más **tests piloto de contrato** antes de tocar lógica de producción.

Esto genera valor inmediato y crea una red de seguridad antes de cualquier refactor.

### Otras Convenciones

- Usar GSD (pre-edit logs) antes de modificar tests o servicios como parte de esta revisión.
- Ejecutar `ruff check --fix` + `pytest -k "<fase>"` antes de dar por terminado cualquier trabajo de una fase.
- Mantener `refactor_testing.md` y `fases_refactor_testing.md` actualizados al final de cada sesión.

---

## 8. Próximos Pasos

Una vez aprobada esta metodología, se procederá de forma **cronológica**:

1. Fases tempranas / Fundación (pre-GSD formal).
2. Fase 07.1 (Alembic).
3. Fase 8 (Testing & Technical Debt) — revisión meta.
4. Fases 9 en adelante, siguiendo el orden de `.planning/phases/`.

---

**Este documento es la fuente de verdad para cómo se realizará la revisión de testing por fase.**

Cualquier ajuste a esta metodología debe reflejarse aquí antes de aplicarse.