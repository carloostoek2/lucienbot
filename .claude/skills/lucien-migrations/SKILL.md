---
name: lucien-migrations
description: Alembic migration patterns for Lucien Bot. Trigger when: creating migrations, adding columns, modifying enums, running alembic commands, or working in the alembic/ directory. This skill provides patterns for safe database migrations with PostgreSQL compatibility.
---

# Lucien Bot — Migraciones

Consultar siempre: `models/CLAUDE.md` (sección Alembic) para cadena de migraciones y reglas detalladas.

## Patrón Enum-First (OBLIGATORIO)

**Antes de usar un nuevo valor de enum en código, crear UNA migración dedicada que agregue el valor al enum.**

```bash
# 1. Crear migración de enum
alembic revision -m "Add MY_VALUE to transaction_source enum"

# 2. Editar la migración para agregar el valor al enum
# 3. Luego usar el enum en código
```

**¿Por qué?** PostgreSQL no permite eliminar valores de enum. Si agregas un enum via SQLAlchemy autogenerate, el downgrade no funciona. Un migrate dedicado con `IF NOT EXISTS` y downgrade documentado es idempotente y seguro.

## Migración para Nuevo Valor de Enum

```python
# alembic/versions/xxxx_add_MY_ENUM_to_transaction_source.py
ENUM_NAME = 'transactionsource'
TABLE_NAME = 'besito_transactions'
COLUMN_NAME = 'source'
NEW_VALUE = 'MY_VALUE'

def upgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == 'postgresql':
        op.execute(f"ALTER TYPE {ENUM_NAME} ADD VALUE IF NOT EXISTS '{NEW_VALUE}'")
    else:
        # SQLite: No action needed
        pass

def downgrade() -> None:
    pass  # PostgreSQL no soporta DROP VALUE
```

## Migración para Agregar Columna

```python
def upgrade() -> None:
    op.add_column(
        'trivia_promotion_configs',
        sa.Column('question_set_id', sa.Integer(),
                 sa.ForeignKey('question_sets.id'), nullable=True)
    )

def downgrade() -> None:
    op.drop_column('trivia_promotion_configs', 'question_set_id')
```

## Reglas para Migraciones

1. **Enum values → migración dedicada** (nunca en la misma migración que crea la tabla que lo usa)
2. **Unique constraints → verificar que no existan duplicados** antes de agregar (`SELECT ... HAVING COUNT(*) > 1`)
3. **Idempotencia** — usar `IF NOT EXISTS` para enum values y constraints
4. **Downgrade** — documentar si PostgreSQL no soporta rollback (ej: enum DROP VALUE)
5. **Testing** — probar `alembic upgrade head` y `alembic downgrade -1` en SQLite local

## Cadena de Migraciones

```
e8de5494e5b6 (base: initial schema)
  └── 9fab8787057e (vip_entry_status/stage)
        └── 287e36271be4 (BigInteger upgrade)
              └── add_selected_emoji_ids
                    └── 499b5924723f (anonymous_messages)
                          └── 41d674ac4f9a (low_stock_threshold)
                                └── 756121049a4a (is_vip_exclusive)
                                      └── c32861733e54 (game_records)
                                            └── 20250406_add_trivia... (TRIVIA enum)
                                                  └── 20250406_manual_file_count
                                                        ├── 20250406_add_category_id_to_packages
                                                        │     └── 20250406_add_category_id_to_store_products
                                                        └── ea7e3c03df29 (merge head)
                                                              └── f7d08ca1ce1a (unique constraint)
                                                                    └── 3f20074a2dd3 (last_reference_id)
                                                                          └── 7c158f7483f5 (cooldown_hours)
                                                                                └── 20250407_add_unique... (unique constraint dup)
                                                                                      └── 20250407_add_game_and_anonymous_message... ← ÚLTIMO
```

## Verificar Integridad de la Cadena

```bash
python -c "
from alembic.config import Config
from alembic.script import ScriptDirectory
cfg = Config('alembic.ini')
script = ScriptDirectory.from_config(cfg)
for rev in reversed(list(script.walk_revisions())):
    parent = rev.down_revision or '(base)'
    print(f'{rev.revision[:30]} <- {str(parent)[:30]}')
"
```

## Base de datos de Producción (Railway PostgreSQL)

- `postgresql://postgres:<password>@gondola.proxy.rlwy.net:53750/railway`
- Ver valores de un enum: `SELECT enumlabel FROM pg_enum WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '<enum_name>') ORDER BY enumlabel;`
- Ver constraint único: `SELECT conname FROM pg_constraint WHERE conrelid = '<table>'::regclass AND contype = 'u';`
- Ver versión: `SELECT * FROM alembic_version;`

## Crear Nueva Migración

```bash
alembic revision -m "descripción clara del cambio"
```