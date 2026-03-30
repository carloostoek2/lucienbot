# Narrative Domain

Narrativa interactiva con arquetipos y nodos de historia.

## Services
- [story_service.py](../story_service.py) - Gestión narrativa

## Handlers
- [story_user_handlers.py](../../handlers/story_user_handlers.py) - Usuario
- [story_admin_handlers.py](../../handlers/story_admin_handlers.py) - Admin

## Modelos
- `StoryNode` - Nodos de narrativa
- `StoryChoice` - Opciones de decisión
- `UserStoryProgress` - Progreso por usuario
- `Archetype` - Arquetipos definidos
- `StoryAchievement` - Logros de narrativa

## StoryService API
```python
- create_node(...)                   # Crear nodo
- create_choice(node_id, ...)         # Crear opción
- advance_to_node(user_id, node_id)  # Avanzar usuario
- calculate_archetype(user_id)       # Calcular arquetipo
- get_user_progress(user_id)         # Obtener progreso
- get_current_node(user_id)           # Nodo actual
```

## Flujo Narrativo
```
Usuario → Nodo actual → Ver opciones → Elegir
  → Avanzar al siguiente nodo
  → Guardar progreso
  → Verificar si requiere VIP
```

## Arquetipos
- Determina el contenido disponible por usuario
- Calculado basándose en decisiones tomadas
- Afecta recomendaciones de contenido

## Reglas de Negocio
- Nodo VIP requiere membresía activa
- Progreso se guarda automáticamente
- Arquetipo determina contenido disponible

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en story_service.py
4. Verificar VIP antes de entregar contenido restringido
