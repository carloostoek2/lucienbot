---
name: lucien-gsd
description: GSD (General-Specific-Do) workflow for Lucien Bot. Trigger when: about to modify files, implement features, fix bugs, or any development task. This skill enforces the mandatory workflow that must be followed before making any code changes.
---

# Lucien Bot — GSD Workflow

**REGLA CRÍTICA:** Antes de usar herramientas que modifiquen archivos, iniciar trabajo a través de GSD.

## Comandos GSD

| Comando | Uso |
|---------|-----|
| `/gsd:quick` | Fixes pequeños, updates de docs, tareas ad-hoc |
| `/gsd:debug` | Investigación y bug fixing |
| `/gsd:execute-phase` | Trabajo planificado por fases |

## Cuándo Usar Cada Comando

### `/gsd:quick`
- Fixes pequeños (typos, bugs очевид)
- Updates de documentación
- Tareas ad-hoc que no requieren investigación
- Cambios en un solo archivo

### `/gsd:debug`
- Investigación de bugs complejos
- Tracing de errores
- Análisis de logs
- Hallazgos que requieren cambios

### `/gsd:execute-phase`
- Nuevas features
- Refactoring significativo
- Migraciones de BD
- Trabajos que requieren múltiples pasos
- Tasks que duran más de unos minutos

## Por Qué GSD es Obligatorio

1. **Consistencia**: Asegura que todo trabajo pase por el mismo proceso
2. **Calidad**: El flujo estructurado captura requisitos antes de implementar
3. **Traza**: Registro de decisiones y cambios
4. **Collaboration**: Otros pueden entender el contexto del trabajo

## Anti-GSD (PROHIBIDO)

❌ **No hacer edits directos** fuera de GSD a menos que el usuario lo pida explícitamente.

```python
# PROHIBIDO: Editar archivos directamente sin GSD
def handle_something(callback: CallbackQuery):
    # No hacer esto
    with open("file.py", "w") as f:
        f.write("new content")
```

✅ **Correcto**: Usar el flujo GSD
1. Usuario pide cambio → agente invoca GSD
2. GSD define el plan → usuario approve
3. GSD ejecuta → resultados

## Excepciones

- **Lectura de archivos**: Glob, Grep, Read no requieren GSD
- **Preguntas**: Solo investigar/consultar no necesita GSD
- **Usuario explícito**: Si el usuario dice "hazlo directamente", se puede proceder

## Referencias

- Para arquitectura: invocar `lucien-architecture` skill
- Para handlers: invocar `lucien-handlers` skill
- Para services: invocar `lucien-services` skill
- Para models/migrations: invocar `lucien-models` / `lucien-migrations` skill
- Para seguridad: invocar `lucien-security` skill