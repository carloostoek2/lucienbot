#!/usr/bin/env python3
"""
scripts/sync_claude.py

Sincroniza los archivos CLAUDE.md del proyecto con el código fuente.
Extrae información de handlers, services, models, config, keyboards, utils
y regenera las secciones AUTO de cada CLAUDE.md.

Uso:
    python scripts/sync_claude.py            # Sync todo
    python scripts/sync_claude.py handlers   # Sync solo handlers
    python scripts/sync_claude.py services   # Sync solo services
    python scripts/sync_claude.py --dry-run  # Muestra qué cambiaría
"""

import ast
import os
import re
import sys
import argparse
from pathlib import Path
from typing import Optional

# ── Rutas ──────────────────────────────────────────────────────────────────────

ROOT = Path(__file__).parent.parent.resolve()
HANDLERS_DIR = ROOT / "handlers"
SERVICES_DIR = ROOT / "services"
MODELS_DIR = ROOT / "models"
CONFIG_DIR = ROOT / "config"
KEYBOARDS_DIR = ROOT / "keyboards"
UTILS_DIR = ROOT / "utils"
SCRIPTS_DIR = ROOT / "scripts"

CLAUDE_FILES = {
    "root":      ROOT / "CLAUDE.md",
    "handlers":  HANDLERS_DIR / "CLAUDE.md",
    "services":  SERVICES_DIR / "CLAUDE.md",
    "models":    MODELS_DIR / "CLAUDE.md",
    "config":    CONFIG_DIR / "CLAUDE.md",
    "keyboards": KEYBOARDS_DIR / "CLAUDE.md",
    "utils":     UTILS_DIR / "CLAUDE.md",
    # submódulos de services
    "services/channels":     SERVICES_DIR / "channels" / "CLAUDE.md",
    "services/gamification": SERVICES_DIR / "gamification" / "CLAUDE.md",
    "services/promotions":   SERVICES_DIR / "promotions" / "CLAUDE.md",
    "services/users":         SERVICES_DIR / "users" / "CLAUDE.md",
    "services/vip":          SERVICES_DIR / "vip" / "CLAUDE.md",
    "services/broadcast":     SERVICES_DIR / "broadcast" / "CLAUDE.md",
    "services/missions":      SERVICES_DIR / "missions" / "CLAUDE.md",
    "services/narrative":     SERVICES_DIR / "narrative" / "CLAUDE.md",
    "services/store":         SERVICES_DIR / "store" / "CLAUDE.md",
}

# ── EXTRACTORS ────────────────────────────────────────────────────────────────

def _safe_read(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _all_py(dir_path: Path) -> list[Path]:
    if not dir_path.is_dir():
        return []
    return sorted([
        p for p in dir_path.iterdir()
        if p.suffix == ".py" and p.name != "__init__.py" and p.name != "__main__.py"
    ])


def _get_docstring(node: ast.AST) -> str:
    """Extrae la docstring de primer nivel de un nodo AST."""
    if (
        isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
    ):
        return node.body[0].value.value or ""
    return ""


# ── HANDLERS ──────────────────────────────────────────────────────────────────

def extract_handlers() -> dict:
    """Extrae estructura de handlers desde __init__.py y archivos."""
    result = {
        "routers": [],   # [(router_name, handler_file, phase_comment)]
        "states": {},    # {handler_file: [(state_group_name, [state_names])]}
        "phases": {},
    }

    init_path = HANDLERS_DIR / "__init__.py"
    if not init_path.exists():
        return result

    source = init_path.read_text(encoding="utf-8")
    phase = "General"
    phase_map = {}

    for line in source.splitlines():
        m = re.match(r"#\s*Phase\s*\d+.*-\s*(.+)", line)
        if m:
            phase = m.group(1).strip()
            continue
        m = re.match(r"#\s*Fase\s*\d+\s*-\s*(.+)", line)
        if m:
            phase = m.group(1).strip()
            continue
        m = re.match(r"\s*from\s+\.(\w+)_handlers\s+import\s+router\s+as\s+(\w+)", line)
        if m:
            handler_file = m.group(1)
            router_name = m.group(2)
            phase_map[handler_file] = phase
            result["routers"].append((router_name, handler_file, phase))

    # Extraer FSM states de cada handler
    for router_name, handler_file, _ in result["routers"]:
        file_path = HANDLERS_DIR / f"{handler_file}_handlers.py"
        if not file_path.exists():
            continue
        source = file_path.read_text(encoding="utf-8")
        states = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("States"):
                state_names = [
                    s.targets[0].id
                    for s in node.body
                    if isinstance(s, ast.Assign)
                    and s.targets
                    and isinstance(s.targets[0], ast.Name)
                    and isinstance(s.value, ast.Call)
                    and getattr(s.value.func, "id", None) == "State"
                ]
                states.append((node.name, state_names))
        if states:
            result["states"][handler_file] = states

    return result


def generate_handlers_claude(handlers_data: dict) -> str:
    """Genera la sección AUTO de handlers/CLAUDE.md."""
    lines = ["```\nhandlers/\n"]
    for router_name, handler_file, phase in handlers_data["routers"]:
        filename = f"{handler_file}_handlers.py"
        states_info = handlers_data["states"].get(handler_file, [])
        states_str = ""
        if states_info:
            state_groups = [f"{g}({', '.join(ss)})" for g, ss in states_info]
            states_str = f"  [{', '.join(state_groups)}]"
        phase_label = f"  # {phase}" if phase != "General" else ""
        lines.append(f"├── {filename}{states_str}{phase_label}\n")
    lines.append("```\n")
    return "".join(lines)


# ── SERVICES ─────────────────────────────────────────────────────────────────

def extract_services() -> dict:
    """Extrae servicios desde __init__.py y archivos."""
    result = {
        "services": [],   # [(class_name, service_file, phase)]
        "methods": {},   # {class_name: [(method_name, params, return_hint)]}
    }

    init_path = SERVICES_DIR / "__init__.py"
    if not init_path.exists():
        return result

    source = init_path.read_text(encoding="utf-8")
    phase = "General"
    phase_map = {}

    for line in source.splitlines():
        m = re.match(r"#\s*Phase\s*\d+.*-\s*(.+)", line)
        if m:
            phase = m.group(1).strip()
            continue
        m = re.match(r"#\s*Fase\s*\d+\s*-\s*(.+)", line)
        if m:
            phase = m.group(1).strip()
            continue
        m = re.match(r"\s*from\s+\.(\w+)_service\s+import\s+(\w+)", line)
        if m:
            service_file = m.group(1)
            class_name = m.group(2)
            phase_map[service_file] = phase
            result["services"].append((class_name, service_file, phase))

    # Extraer métodos de cada service
    for class_name, service_file, _ in result["services"]:
        file_path = SERVICES_DIR / f"{service_file}_service.py"
        if not file_path.exists():
            # intentar sin _service (ej: scheduler_service.py → SchedulerService)
            candidates = list(SERVICES_DIR.glob(f"{service_file}*.py"))
            if candidates:
                file_path = candidates[0]
            else:
                continue
        source = file_path.read_text(encoding="utf-8")
        methods = []
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                doc = _get_docstring(node)
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                        args = [
                            a.arg for a in item.args.args
                            if a.arg != "self"
                        ]
                        ret = ""
                        if item.returns and isinstance(item.returns, ast.Name):
                            ret = f" -> {item.returns.id}"
                        methods.append((item.name, args, ret, doc))
        if methods:
            result["methods"][class_name] = methods

    return result


def generate_services_claude(services_data: dict) -> str:
    """Genera la sección AUTO de services/CLAUDE.md."""
    lines = ["| Service | Dominio | Archivo | Métodos |\n", "|---------|---------|---------|--------|\n"]
    domain_map = {
        "ChannelService": "Channels",
        "VIPService": "VIP",
        "UserService": "Users",
        "SchedulerService": "System",
        "BesitoService": "Gamificación",
        "BroadcastService": "Broadcast",
        "DailyGiftService": "Gamificación",
        "PackageService": "Store",
        "MissionService": "Missions",
        "RewardService": "Missions",
        "StoreService": "Store",
        "PromotionService": "Promotions",
        "StoryService": "Narrative",
        "AnalyticsService": "Analytics",
        "BackupService": "System",
    }
    method_map = services_data.get("methods", {})
    for class_name, service_file, phase in services_data["services"]:
        domain = domain_map.get(class_name, service_file.title())
        methods = method_map.get(class_name, [])
        method_list = ", ".join(m[0] for m in methods[:5])
        if len(methods) > 5:
            method_list += f", +{len(methods)-5} más"
        lines.append(f"| `{class_name}` | {domain} | `{service_file}_service.py` | {method_list} |\n")
    return "".join(lines)


def generate_domain_claude(domain: str, class_name: str, service_file: str,
                            handler_file: str, services_data: dict,
                            handlers_data: dict) -> dict:
    """Genera las secciones AUTO de un CLAUDE.md de submódulo de services."""
    methods = services_data.get("methods", {}).get(class_name, [])
    api_lines = [f"## {class_name} API\n", "```python\n"]
    for name, args, ret, doc in methods:
        args_str = ", ".join(args)
        api_lines.append(f"- {name}({args_str}){ret}  {doc}\n")
    api_lines.append("```\n")
    api_section = "".join(api_lines)

    handler_file_path = HANDLERS_DIR / f"{handler_file}_handlers.py"
    handler_exists = handler_file_path.exists()
    handlers_section = (
        f"- [{handler_file}_handlers.py](../../handlers/{handler_file}_handlers.py)"
        f"{' - Admin' if 'admin' in handler_file else ' - Usuario' if 'user' in handler_file else ''}\n"
    )

    service_file_path = SERVICES_DIR / f"{service_file}_service.py"
    service_exists = service_file_path.exists()
    services_section = (
        f"- [{service_file}_service.py](../{service_file}_service.py)\n"
    )

    return {
        "api": api_section,
        "handlers": handlers_section,
        "services": services_section,
        "service_exists": service_exists,
        "handler_exists": handler_exists,
    }


# ── MODELS ────────────────────────────────────────────────────────────────────

def extract_models() -> dict:
    """Extrae modelos SQLAlchemy desde models/models.py."""
    result = {
        "models": [],    # [(class_name, docstring, relationships)]
        "enums": [],
    }
    models_path = MODELS_DIR / "models.py"
    if not models_path.exists():
        return result

    source = models_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            doc = _get_docstring(node)
            # Detectar si es Enum
            is_enum = "Enum" in [b.id for b in node.bases if isinstance(b, ast.Name)]

            rels = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if getattr(child.func, "id", None) == "relationship":
                        if child.args and isinstance(child.args[0], ast.Constant):
                            rels.append(child.args[0].value)
                        elif child.keywords:
                            for kw in child.keywords:
                                if kw.arg == "back_populates":
                                    rels.append(f"→ {getattr(kw.value, 'id', '')}")
            if is_enum:
                result["enums"].append((node.name, doc))
            else:
                result["models"].append((node.name, doc, rels))
    return result


def generate_models_claude(models_data: dict) -> str:
    """Genera la sección AUTO de models/CLAUDE.md."""
    lines = [
        "| Modelo | Descripción | Relaciones |\n",
        "|--------|-------------|------------|\n",
    ]
    for name, doc, rels in models_data["models"]:
        rel_str = ", ".join(rels) if rels else "-"
        lines.append(f"| `{name}` | {doc or '—'} | {rel_str} |\n")
    return "".join(lines)


# ── CONFIG ────────────────────────────────────────────────────────────────────

def extract_config() -> dict:
    """Extrae variables de entorno desde config/settings.py."""
    result = {"fields": []}  # [(field_name, env_var, default, doc)]
    settings_path = CONFIG_DIR / "settings.py"
    if not settings_path.exists():
        return result

    source = settings_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name.endswith("Config"):
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                    field = item.target.id
                    env_var = field
                    default = ""
                    if isinstance(item.value, ast.Call):
                        func = item.value.func
                        if getattr(func, "id", None) == "getenv":
                            args = item.value.args
                            if args and isinstance(args[0], ast.Constant):
                                env_var = args[0].value or field
                            if len(args) >= 2 and isinstance(args[1], ast.Constant):
                                default = repr(args[1].value)
                    result["fields"].append((field, env_var, default, ""))
    return result


def generate_config_claude(config_data: dict) -> str:
    """Genera la sección AUTO de config/CLAUDE.md."""
    lines = ["```bash\n"]
    for field, env_var, default, doc in config_data["fields"]:
        if default:
            lines.append(f"# {doc}\n{env_var}={default}\n\n")
        else:
            lines.append(f"# {doc}\n{env_var}=\n\n")
    lines.append("```\n")
    return "".join(lines)


# ── KEYBOARDS ─────────────────────────────────────────────────────────────────

def extract_keyboards() -> dict:
    """Extrae funciones de teclado desde keyboards/inline_keyboards.py."""
    result = {"functions": []}  # [(name, params, doc)]
    kb_path = KEYBOARDS_DIR / "inline_keyboards.py"
    if not kb_path.exists():
        return result

    source = kb_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return result

    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            args = [a.arg for a in node.args.args]
            doc = _get_docstring(node) or "Inline keyboard"
            result["functions"].append((node.name, args, doc))
    return result


def generate_keyboards_claude(kb_data: dict) -> str:
    """Genera la sección AUTO de keyboards/CLAUDE.md."""
    lines = ["| Función | Descripción |\n", "|---------|-------------|\n"]
    for name, args, doc in kb_data["functions"]:
        params = ", ".join(a for a in args if a != "self")
        lines.append(f"| `{name}({params})` | {doc} |\n")
    return "".join(lines)


# ── UTILS ────────────────────────────────────────────────────────────────────

def extract_utils() -> dict:
    """Extrae funciones de utils."""
    result = {"functions": [], "voice_methods": []}
    for py_file in (UTILS_DIR).glob("*.py"):
        if py_file.name in ("__init__.py", "__main__.py"):
            continue
        source = py_file.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                args = [a.arg for a in node.args.args]
                doc = _get_docstring(node) or ""
                result["functions"].append((node.name, args, doc, py_file.stem))
            elif isinstance(node, ast.ClassDef):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith("_"):
                        args = [a.arg for a in item.args.args if a.arg != "self"]
                        doc = _get_docstring(item) or ""
                        result["voice_methods"].append((item.name, args, doc, node.name))
    return result


def generate_utils_claude(utils_data: dict) -> str:
    """Genera la sección AUTO de utils/CLAUDE.md."""
    lines = ["| Módulo | Función | Descripción |\n", "|--------|---------|-------------|\n"]
    for name, args, doc, module in utils_data["functions"]:
        lines.append(f"| `{module}` | `{name}({', '.join(args)})` | {doc} |\n")
    if utils_data["voice_methods"]:
        lines.append("\n### LucienVoice\n\n")
        lines.append("| Método | Descripción |\n")
        lines.append("|--------|-------------|\n")
        for name, args, doc, cls in utils_data["voice_methods"]:
            lines.append(f"| `{name}({', '.join(args)})` | {doc} |\n")
    return "".join(lines)


# ── ROOT CLAUDE ───────────────────────────────────────────────────────────────

def generate_root_claude_services_section(services_data: dict) -> str:
    """Genera la tabla de dominios para CLAUDE.md raíz."""
    lines = ["| Dominio | Service | Archivo |\n", "|---------|---------|--------|\n"]
    for class_name, service_file, phase in services_data["services"]:
        lines.append(f"| {class_name.replace('Service','')} | `{class_name}` | [@services/{service_file}_service.py] |\n")
    return "".join(lines)


def generate_root_claude_handlers_section(handlers_data: dict) -> str:
    """Genera la estructura de handlers para CLAUDE.md raíz."""
    lines = ["```\nhandlers/\n"]
    current_phase = None
    for router_name, handler_file, phase in handlers_data["routers"]:
        if phase != current_phase:
            lines.append(f"# {phase}\n")
            current_phase = phase
        lines.append(f"├── {handler_file}_handlers.py\n")
    lines.append("```\n")
    return "".join(lines)


# ── BLOCK PARSER ─────────────────────────────────────────────────────────────

def parse_claude_with_blocks(content: str) -> dict:
    """
    Parsea un CLAUDE.md extrayendo bloques AUTO y MANUAL.
    Devuelve:
      {
        'auto_blocks': {section_name: content},
        'manual_blocks': [(section_name, content)],
        'gaps': [(before_auto, after_auto)],  # contenido fuera de bloques
      }
    """
    auto_pattern = re.compile(r"<!--\s*AUTO:(\w+)\s*-->\n?(.*?)(?=<!--\s*AUTO:|\Z)", re.DOTALL)
    manual_pattern = re.compile(r"<!--\s*MANUAL:(\w+)\s*START\s*-->(.*?)<!--\s*MANUAL:\1\s*END\s*-->", re.DOTALL)

    auto_blocks = {}
    for m in auto_pattern.finditer(content):
        auto_blocks[m.group(1)] = m.group(2).rstrip()

    manual_blocks = {}
    for m in manual_pattern.finditer(content):
        manual_blocks[m.group(1)] = m.group(2).strip()

    return {"auto_blocks": auto_blocks, "manual_blocks": manual_blocks}


def build_claude_with_blocks(
    auto_blocks: dict,
    manual_blocks: dict,
    template: str,
) -> str:
    """
    Reconstruye un CLAUDE.md substituyendo bloques AUTO desde auto_blocks
    y preservando MANUAL blocks en su lugar.
    """
    result = template
    for section, content in auto_blocks.items():
        marker = f"<!-- AUTO:{section} -->"
        if marker in result:
            result = result.replace(marker, f"<!-- AUTO:{section} -->\n{content}\n<!-- /AUTO:{section} -->")
    return result


# ── TEMPLATES ────────────────────────────────────────────────────────────────

ROOT_CLAUDE_TEMPLATE = """\
# Lucien Bot

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández).

## Quick Commands
```bash
python bot.py                    # Iniciar bot
```

## Arquitectura
```
handlers/ → services/ → models/ → database
```
- **handlers/**: Solo enrutan eventos, SIN lógica de negocio
- **services/**: Lógica de negocio por dominio (un service = un dominio)
- **models/**: Entidades y acceso a DB

## Dominios

<!-- AUTO:SERVICES -->

## Handlers

<!-- AUTO:HANDLERS -->

## Documentos de Referencia
- [@architecture.md] - Reglas de arquitectura (CAPAS PROHIBIDAS)
- [@rules.md] - Reglas del sistema (50 líneas máx, sin lógica en handlers)
- [@decisions.md] - Decisiones técnicas
- [@AGENTS.md] - Documentación técnica completa

<!-- MANUAL:RULES -->
## Reglas Críticas
1. **PROHIBIDO** lógica en handlers
2. **PROHIBIDO** acceso a DB fuera de models
3. **PROHIBIDO** duplicación entre services
4. Funciones máximo 50 líneas
5. Nombrar: verbo + contexto + resultado

## Voz de Lucien
- Habla en 3ra persona ("Lucien gestiona...")
- Elegante, misterioso, nunca vulgar
- "Diana" como figura central
- "Visitantes" no "usuarios"
- "Custodios" no "admins"

## Seguridad
- Validar IDs de callback
- Verificar permisos admin
- Verificar saldos antes de transacciones
- Usar transacciones en BD
<!-- /MANUAL:RULES -->

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Lucien Bot**

Telegram bot gamificado para la comunidad de Señorita Kinky (Diana Hernández). Gestiona suscripciones VIP, canales de contenido, un sistema de gamificación con besitos, misiones, tienda virtual, promociones y narrativa interactiva con arquetipos de personajes.

**Core Value:** Crear una experiencia premium y gamificada que incentiva el compromiso de la comunidad con Diana a través de un sistema de recompensas, acceso exclusivo VIP y narrativa inmersiva.

### Constraints

- **Tech stack**: Python 3.12+, aiogram 3.x, SQLAlchemy 2.0 — no cambiar sin razón
- **Arquitectura**: Capas handlers/services/models estrictas — sin lógica de negocio en handlers
- **Voz de Lucien**: Siempre en 3ra persona, elegante y misterioso, "Diana" como figura central
- **DB**: SQLite local / PostgreSQL en Railway — compatible SQLAlchemy
- **Sin tests**: Prioridad alta pero no bloqueable para features
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile
<!-- GSD:profile-end -->
"""

# Triple backtick resuelto por código para evitar conflictos en triple-quoted strings
_BT = "\x60"          # backtick
_BT3 = _BT * 3        # ```

_CODE_EXAMPLES = {
    "handlers_correcto": (
        "async def handle_besitos_balance(callback: CallbackQuery, service: BesitoService):\n"
        "    \"\"\"Solo llama al service, no tiene lógica.\"\"\"\n"
        "    user_id = callback.from_user.id\n"
        "    balance = await service.get_balance(user_id)\n"
        "    await callback.message.edit_text(f\"Tu saldo: {balance}\")"
    ),
    "handlers_incorrecto": (
        "async def handle_besitos_balance(callback: CallbackQuery):\n"
        "    # \u274c L\u00f3gica en handler\n"
        "    user = await session.get(User, callback.from_user.id)\n"
        "    user.besitos += 10  # \u274c L\u00f3gica de negocio\n"
        "    await session.commit()  # \u274c Acceso a DB"
    ),
    "services_db": (
        "from models import User, BesitoTransaction\n\n"
        "# Correcto\n"
        "user = await session.get(User, user_id)\n"
        "# Incorrecto\n"
        "await session.execute(text(\"SELECT * FROM users\"))"
    ),
    "models_db": (
        f"{_BT3}python\n"
        "from models import User\n"
        "from models.database import get_session\n\n"
        "async def get_user(user_id: int):\n"
        "    async with get_session() as session:\n"
        "        return await session.get(User, user_id)\n"
        f"{_BT3}"
    ),
    "config_usage": (
        "from config.settings import settings\n\n"
        "# Uso\n"
        "bot_token = settings.BOT_TOKEN\n"
        "admin_ids = settings.ADMIN_IDS"
    ),
    "keyboards_usage": (
        "from keyboards.inline_keyboards import main_menu_keyboard\n\n"
        "await message.answer(\n"
        "    \"Texto\",\n"
        "    reply_markup=main_menu_keyboard()\n"
        ")"
    ),
}

HANDLERS_CLAUDE_TEMPLATE = """\
# Handlers

Solo enrutan eventos desde Telegram. **SIN lógica de negocio, SIN acceso a DB.**

## Estructura

<!-- AUTO:STRUCTURE -->

## Reglas de Handlers

1. **UN service** por handler
2. **SIN lógica** de negocio
3. **SIN acceso** directo a DB
4. **Logging** de eventos recibidos

## Ejemplo Correcto

`""" + _CODE_EXAMPLES["handlers_correcto"] + """`

## Ejemplo Incorrecto (PROHIBIDO)

`""" + _CODE_EXAMPLES["handlers_incorrecto"] + """`
"""

SERVICES_CLAUDE_TEMPLATE = """\
# Services

Lógica de negocio por dominio. Un service = un dominio (no fragmentar).

## Servicios Disponibles

<!-- AUTO:SERVICES -->

## Reglas de Services

- Un service es dueño de su dominio
- Centraliza toda la lógica del dominio
- **PROHIBIDO**: lógica duplicada en múltiples services
- **PROHIBIDO**: acceso a DB directo (usar models)
- Funciones máximo 50 líneas
- Logging en cada acción importante

## Acceso a DB

Los services NO acceden a DB directamente. Usan models:

`""" + _CODE_EXAMPLES["services_db"] + """`
"""

MODELS_CLAUDE_TEMPLATE = """\
# Models

Entidades de SQLAlchemy y acceso a base de datos.

## Archivos
- [models.py](models.py) - Todos los modelos
- [database.py](database.py) - Configuración de conexión

## Modelos Principales

<!-- AUTO:MODELS -->

## Acceso a DB

`""" + _CODE_EXAMPLES["models_db"] + """`

## Reglas

- Usar ORM (SQLAlchemy), **nunca** SQL raw
- Transacciones para operaciones atómicas
- Historial inmutable (besitos)
"""

CONFIG_CLAUDE_TEMPLATE = """\
# Config

Configuración global del bot.

## Archivos
- [settings.py](settings.py) - Configuración y variables de entorno

## Variables de Entorno

<!-- AUTO:ENV_VARS -->

## Acceso a Config
`""" + _CODE_EXAMPLES["config_usage"] + """`

## Reglas
- **NUNCA** hardcodear tokens o IDs
- Usar variables de entorno siempre
- No subir .env a git

## railway.toml
Configuración de despliegue en Railway.
"""

KEYBOARDS_CLAUDE_TEMPLATE = """\
# Keyboards

Teclados inline de Telegram.

## Archivos
- [inline_keyboards.py](inline_keyboards.py) - Definición de todos los teclados

## Tipos de Teclados

<!-- AUTO:KEYBOARDS -->

## Uso
`""" + _CODE_EXAMPLES["keyboards_usage"] + """`

## Reglas
- Un teclado por contexto
- Mantener简洁 (no más de 3 filas)
- Siempre incluir "Atrás"

## Voice de Teclados
- Usar texto elegante
- "Regesar" no "Volver"
- "Confirmar" para acciones irreversibles
"""

UTILS_CLAUDE_TEMPLATE = """\
# Utils

Utilidades y helpers del bot.

## Archivos
- [helpers.py](helpers.py) - Funciones helper
- [lucien_voice.py](lucien_voice.py) - Plantillas de mensajes

<!-- AUTO:FUNCTIONS -->

## Reglas
- **NUNCA** lógica de negocio en utils
- Solo helpers puros (sin efectos secundarios)
- Voice de Lucien: siempre elegante y misterioso
"""

DOMAIN_CLAUDE_TEMPLATE = """\
# {domain_name} Domain

{domain_description}

## Services
<!-- AUTO:SERVICES -->

## Handlers
<!-- AUTO:HANDLERS -->

<!-- MANUAL:BUSINESS_RULES -->
## Reglas de Negocio
- *(Reglas de negocio específicas del dominio)*
<!-- /MANUAL:BUSINESS_RULES -->

## Antes de Implementar
1. Lee [@architecture.md](../../architecture.md)
2. Lee [@rules.md](../../rules.md)
3. Verifica métodos existentes en el service
4. No duplicar lógica entre services
"""


# ── SYNC FUNCTIONS ───────────────────────────────────────────────────────────

def sync_handlers(dry_run: bool = False) -> str:
    """Sincroniza handlers/CLAUDE.md"""
    handlers_data = extract_handlers()
    auto_content = generate_handlers_claude(handlers_data)

    path = CLAUDE_FILES["handlers"]
    if dry_run:
        return f"[handlers/CLAUDE.md]\n{auto_content}"

    content = _safe_read(path) if path.exists() else HANDLERS_CLAUDE_TEMPLATE
    # Reemplazar bloque AUTO
    new_content = re.sub(
        r"(<!--\s*AUTO:STRUCTURE\s*-->).*?(<!--\s*/AUTO:STRUCTURE\s*-->)",
        r"\1\n" + auto_content + r"\2",
        content,
        flags=re.DOTALL
    )
    if "<!-- AUTO:STRUCTURE -->" not in new_content:
        # Insertar en template
        new_content = HANDLERS_CLAUDE_TEMPLATE.replace(
            "<!-- AUTO:STRUCTURE -->",
            "<!-- AUTO:STRUCTURE -->\n" + auto_content + "\n"
        )
    path.write_text(new_content, encoding="utf-8")
    return f"[handlers/CLAUDE.md] ✓"


def sync_services(dry_run: bool = False) -> str:
    """Sincroniza services/CLAUDE.md"""
    services_data = extract_services()
    auto_content = generate_services_claude(services_data)

    path = CLAUDE_FILES["services"]
    if dry_run:
        return f"[services/CLAUDE.md]\n{auto_content}"

    content = _safe_read(path) if path.exists() else SERVICES_CLAUDE_TEMPLATE
    new_content = re.sub(
        r"(<!--\s*AUTO:SERVICES\s*-->).*?(<!--\s*/AUTO:SERVICES\s*-->)",
        r"\1\n" + auto_content + r"\2",
        content,
        flags=re.DOTALL
    )
    if "<!-- AUTO:SERVICES -->" not in new_content:
        new_content = SERVICES_CLAUDE_TEMPLATE.replace(
            "<!-- AUTO:SERVICES -->",
            "<!-- AUTO:SERVICES -->\n" + auto_content + "\n"
        )
    path.write_text(new_content, encoding="utf-8")
    return f"[services/CLAUDE.md] ✓"


def sync_models(dry_run: bool = False) -> str:
    """Sincroniza models/CLAUDE.md"""
    models_data = extract_models()
    auto_content = generate_models_claude(models_data)

    path = CLAUDE_FILES["models"]
    if dry_run:
        return f"[models/CLAUDE.md]\n{auto_content}"

    content = _safe_read(path) if path.exists() else MODELS_CLAUDE_TEMPLATE
    new_content = re.sub(
        r"(<!--\s*AUTO:MODELS\s*-->).*?(<!--\s*/AUTO:MODELS\s*-->)",
        r"\1\n" + auto_content + r"\2",
        content,
        flags=re.DOTALL
    )
    if "<!-- AUTO:MODELS -->" not in new_content:
        new_content = MODELS_CLAUDE_TEMPLATE.replace(
            "<!-- AUTO:MODELS -->",
            "<!-- AUTO:MODELS -->\n" + auto_content + "\n"
        )
    path.write_text(new_content, encoding="utf-8")
    return f"[models/CLAUDE.md] ✓"


def sync_config(dry_run: bool = False) -> str:
    """Sincroniza config/CLAUDE.md"""
    config_data = extract_config()
    auto_content = generate_config_claude(config_data)

    path = CLAUDE_FILES["config"]
    if dry_run:
        return f"[config/CLAUDE.md]\n{auto_content}"

    content = _safe_read(path) if path.exists() else CONFIG_CLAUDE_TEMPLATE
    new_content = re.sub(
        r"(<!--\s*AUTO:ENV_VARS\s*-->).*?(<!--\s*/AUTO:ENV_VARS\s*-->)",
        r"\1\n" + auto_content + r"\2",
        content,
        flags=re.DOTALL
    )
    if "<!-- AUTO:ENV_VARS -->" not in new_content:
        new_content = CONFIG_CLAUDE_TEMPLATE.replace(
            "<!-- AUTO:ENV_VARS -->",
            "<!-- AUTO:ENV_VARS -->\n" + auto_content + "\n"
        )
    path.write_text(new_content, encoding="utf-8")
    return f"[config/CLAUDE.md] ✓"


def sync_keyboards(dry_run: bool = False) -> str:
    """Sincroniza keyboards/CLAUDE.md"""
    kb_data = extract_keyboards()
    auto_content = generate_keyboards_claude(kb_data)

    path = CLAUDE_FILES["keyboards"]
    if dry_run:
        return f"[keyboards/CLAUDE.md]\n{auto_content}"

    content = _safe_read(path) if path.exists() else KEYBOARDS_CLAUDE_TEMPLATE
    new_content = re.sub(
        r"(<!--\s*AUTO:KEYBOARDS\s*-->).*?(<!--\s*/AUTO:KEYBOARDS\s*-->)",
        r"\1\n" + auto_content + r"\2",
        content,
        flags=re.DOTALL
    )
    if "<!-- AUTO:KEYBOARDS -->" not in new_content:
        new_content = KEYBOARDS_CLAUDE_TEMPLATE.replace(
            "<!-- AUTO:KEYBOARDS -->",
            "<!-- AUTO:KEYBOARDS -->\n" + auto_content + "\n"
        )
    path.write_text(new_content, encoding="utf-8")
    return f"[keyboards/CLAUDE.md] ✓"


def sync_utils(dry_run: bool = False) -> str:
    """Sincroniza utils/CLAUDE.md"""
    utils_data = extract_utils()
    auto_content = generate_utils_claude(utils_data)

    path = CLAUDE_FILES["utils"]
    if dry_run:
        return f"[utils/CLAUDE.md]\n{auto_content}"

    content = _safe_read(path) if path.exists() else UTILS_CLAUDE_TEMPLATE
    new_content = re.sub(
        r"(<!--\s*AUTO:FUNCTIONS\s*-->).*?(<!--\s*/AUTO:FUNCTIONS\s*-->)",
        r"\1\n" + auto_content + r"\2",
        content,
        flags=re.DOTALL
    )
    if "<!-- AUTO:FUNCTIONS -->" not in new_content:
        new_content = UTILS_CLAUDE_TEMPLATE.replace(
            "<!-- AUTO:FUNCTIONS -->",
            "<!-- AUTO:FUNCTIONS -->\n" + auto_content + "\n"
        )
    path.write_text(new_content, encoding="utf-8")
    return f"[utils/CLAUDE.md] ✓"


def sync_root(dry_run: bool = False) -> str:
    """Sincroniza CLAUDE.md raíz (dominios + handlers)."""
    services_data = extract_services()
    handlers_data = extract_handlers()

    services_section = generate_root_claude_services_section(services_data)
    handlers_section = generate_root_claude_handlers_section(handlers_data)

    path = CLAUDE_FILES["root"]
    if dry_run:
        return (
            f"[CLAUDE.md SERVICES]\n{services_section}\n\n"
            f"[CLAUDE.md HANDLERS]\n{handlers_section}"
        )

    content = _safe_read(path) if path.exists() else ROOT_CLAUDE_TEMPLATE

    content = re.sub(
        r"(<!--\s*AUTO:SERVICES\s*-->).*?(<!--\s*/AUTO:SERVICES\s*-->)",
        r"\1\n" + services_section + r"\2",
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r"(<!--\s*AUTO:HANDLERS\s*-->).*?(<!--\s*/AUTO:HANDLERS\s*-->)",
        r"\1\n" + handlers_section + r"\2",
        content,
        flags=re.DOTALL
    )

    # Si no existen bloques, crear template con estructura base
    if "<!-- AUTO:SERVICES -->" not in content:
        # Solo actualizar la tabla Dominios que ya existe
        content = _safe_read(path) if path.exists() else ROOT_CLAUDE_TEMPLATE

    path.write_text(content, encoding="utf-8")
    return f"[CLAUDE.md] ✓"


# ── DOMAIN SYNC ─────────────────────────────────────────────────────────────

DOMAIN_MAP = {
    "services/vip":          ("VIPService",     "vip",          "vip",          "VIP — Membresías exclusivas"),
    "services/gamification": ("BesitoService",   "besito",       "gamification", "Gamificación — Besitos y recompensas"),
    "services/channels":     ("ChannelService",  "channel",      "channel",      "Channels — Gestión de canales"),
    "services/broadcast":    ("BroadcastService","broadcast",     "broadcast",    "Broadcast — Difusión masiva"),
    "services/missions":     ("MissionService",  "mission",      "mission",      "Missions — Tareas y recompensas"),
    "services/store":         ("StoreService",    "store",        "store",        "Store — Tienda virtual"),
    "services/promotions":    ("PromotionService","promotion",    "promotion",    "Promotions — Promociones comerciales"),
    "services/narrative":     ("StoryService",    "story",        "story",        "Narrative — Historia interactiva"),
    "services/users":         ("UserService",     "user",         "user",         "Users — Perfiles de usuario"),
}


def sync_domain(domain_key: str, dry_run: bool = False) -> str:
    """Sincroniza un CLAUDE.md de submódulo de services."""
    if domain_key not in DOMAIN_MAP:
        return f"[{domain_key}] Desconocido — ignora"

    class_name, service_file, handler_file, domain_desc = DOMAIN_MAP[domain_key]

    services_data = extract_services()
    handlers_data = extract_handlers()
    methods = services_data.get("methods", {}).get(class_name, [])

    # API section
    api_lines = ["## API\n", "```python\n"]
    for name, args, ret, doc in methods:
        api_lines.append(f"- {name}({', '.join(args)}){ret}\n")
    api_lines.append("```\n")
    api_section = "".join(api_lines)

    # Services section
    service_rel = service_file.replace("_service", "")
    services_section = f"- [{service_file}_service.py](../{service_file}_service.py)\n"

    # Handlers section
    handlers_section = ""
    for router_name, hf, phase in handlers_data["routers"]:
        if hf == handler_file:
            suffix = "Admin" if "admin" in hf else "User" if "user" in hf else ""
            handlers_section = f"- [{hf}_handlers.py](../../handlers/{hf}_handlers.py)\n"
            break

    path = CLAUDE_FILES.get(domain_key)
    if not path:
        return f"[{domain_key}] Sin path — ignora"

    if dry_run:
        return (
            f"[{domain_key}/CLAUDE.md]\n"
            f"SERVICES:\n{services_section}\n"
            f"HANDLERS:\n{handlers_section}\n"
            f"API:\n{api_section}"
        )

    if not path.exists():
        # Crear desde template
        content = DOMAIN_CLAUDE_TEMPLATE.format(
            domain_name=domain_desc.split("—")[0].strip(),
            domain_description=domain_desc.split("—")[1].strip() if "—" in domain_desc else domain_desc,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        content = _safe_read(path)

    content = re.sub(
        r"(<!--\s*AUTO:SERVICES\s*-->).*?(<!--\s*/AUTO:SERVICES\s*-->)",
        r"\1\n" + services_section + r"\2",
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r"(<!--\s*AUTO:HANDLERS\s*-->).*?(<!--\s*/AUTO:HANDLERS\s*-->)",
        r"\1\n" + handlers_section + r"\2",
        content,
        flags=re.DOTALL
    )
    content = re.sub(
        r"(<!--\s*AUTO:API\s*-->).*?(<!--\s*/AUTO:API\s*-->)",
        r"\1\n" + api_section + r"\2",
        content,
        flags=re.DOTALL
    )

    path.write_text(content, encoding="utf-8")
    return f"[{domain_key}/CLAUDE.md] ✓"


# ── CLI ──────────────────────────────────────────────────────────────────────

def detect_module_from_file(file_path: str) -> list[str]:
    """Dado un archivo modificado, devuelve qué CLAUDE.md deben actualizarse."""
    file_path = file_path.replace("\\", "/")
    modules = []

    if "/handlers/" in file_path:
        modules.append("handlers")
        # Buscar domain handler
        for domain_key in DOMAIN_MAP:
            _, _, handler_file, _ = DOMAIN_MAP[domain_key]
            if handler_file in file_path:
                modules.append(domain_key)
                break

    if "/services/" in file_path:
        modules.append("services")
        modules.append("root")
        for domain_key, (class_name, service_file, _, _) in DOMAIN_MAP.items():
            if service_file in file_path:
                modules.append(domain_key)
                break

    if "/models/" in file_path:
        modules.extend(["models", "root"])

    if "/config/" in file_path:
        modules.append("config")

    if "/keyboards/" in file_path:
        modules.append("keyboards")

    if "/utils/" in file_path:
        modules.append("utils")

    if file_path.endswith(".py") and "/handlers/" not in file_path and "/services/" not in file_path and "/models/" not in file_path and "/config/" not in file_path and "/keyboards/" not in file_path and "/utils/" not in file_path:
        modules.extend(["root", "handlers", "services"])

    return list(dict.fromkeys(modules))  # deduplicado preservando orden


SYNC_FN = {
    "handlers": sync_handlers,
    "services": sync_services,
    "models": sync_models,
    "config": sync_config,
    "keyboards": sync_keyboards,
    "utils": sync_utils,
    "root": sync_root,
    "services/vip":          lambda dry_run: sync_domain("services/vip", dry_run),
    "services/gamification":  lambda dry_run: sync_domain("services/gamification", dry_run),
    "services/channels":      lambda dry_run: sync_domain("services/channels", dry_run),
    "services/broadcast":     lambda dry_run: sync_domain("services/broadcast", dry_run),
    "services/missions":      lambda dry_run: sync_domain("services/missions", dry_run),
    "services/store":         lambda dry_run: sync_domain("services/store", dry_run),
    "services/promotions":    lambda dry_run: sync_domain("services/promotions", dry_run),
    "services/narrative":     lambda dry_run: sync_domain("services/narrative", dry_run),
    "services/users":         lambda dry_run: sync_domain("services/users", dry_run),
}

ALL_MODULES = ["root", "handlers", "services", "models", "config", "keyboards", "utils",
               "services/vip", "services/gamification", "services/channels",
               "services/broadcast", "services/missions", "services/store",
               "services/promotions", "services/narrative", "services/users"]


def main():
    parser = argparse.ArgumentParser(description="Sincroniza archivos CLAUDE.md con el código fuente")
    parser.add_argument("modules", nargs="*", default=[], help="Módulos a sincronizar (o 'all')")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar qué cambiaría")
    parser.add_argument("--file", help="Detectar módulos automáticamente desde un archivo modificado")
    args = parser.parse_args()

    if args.file:
        modules = detect_module_from_file(args.file)
        if not modules:
            print(f"No se detectaron módulos para: {args.file}")
            sys.exit(0)
        print(f"Detectado: {', '.join(modules)}")
    elif args.modules and args.modules[0] != "all":
        modules = args.modules
    else:
        modules = ALL_MODULES

    results = []
    for module in modules:
        fn = SYNC_FN.get(module)
        if fn:
            try:
                result = fn(dry_run=args.dry_run)
                results.append(result)
            except Exception as e:
                results.append(f"[{module}] ERROR: {e}")
        else:
            results.append(f"[{module}] Sin función de sync — ignora")

    print("\n".join(results))
    if not args.dry_run:
        print(f"\n✓ Sync completado — {len([r for r in results if '✓' in r])} archivos actualizados")
    else:
        print(f"\n(Dry-run — ningún archivo modificado)")


if __name__ == "__main__":
    main()
