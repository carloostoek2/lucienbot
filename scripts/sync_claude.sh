#!/usr/bin/env bash
# scripts/sync_claude.sh
# Sincroniza archivos CLAUDE.md con el código fuente
#
# Uso:
#   ./scripts/sync_claude.sh           # Sync todo
#   ./scripts/sync_claude.sh handlers  # Sync solo handlers
#   ./scripts/sync_claude.sh --dry-run # Ver qué cambiaría
#   ./scripts/sync_claude.sh --file X  # Auto-detectar módulo desde archivo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

python scripts/sync_claude.py "$@"
