#!/usr/bin/env python3
"""
Script de Tests Críticos - Lucien Bot

Ejecuta únicamente los tests de flujos de máxima importancia.
Fácil de extender: agregar nuevos tests a la lista CRITICAL_TESTS.

Uso:
    python run_critical_tests.py          # Ejecutar todos los tests críticos
    python run_critical_tests.py --list   # Listar solo los tests sin ejecutar
    python run_critical_tests.py --help   # Mostrar ayuda
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ==================== CONFIGURACIÓN ====================

# Tests críticos - agregar más aquí según necesidad
CRITICAL_TESTS = {
    # Flujo de Misiones (E2E)
    "tests/integration/test_mission_e2e.py": [
        "test_reaction_triggers_mission_and_grants_besitos",
        "test_partial_reaction_does_not_complete_mission",
        "test_recurring_mission_resets_after_completion",
    ],
    # Integridad de Migraciones Alembic
    "tests/integration/test_alembic_heads.py": [
        "test_alembic_single_head_no_branches",
        "test_alembic_current_revision_matches_head",
        "test_alembic_history_no_gaps",
    ],
    # Ciclo Completo VIP
    "tests/integration/test_vip_complete_cycle.py": [
        "test_vip_entry_token_to_subscription",
        "test_vip_reminder_24h_before_expiration",
        "test_vip_expiration_and_deactivation",
        "test_vip_complete_lifecycle_integration",
    ],
    # Límite de Reacciones (documenta gap)
    "tests/integration/test_reaction_limit.py": [
        "test_no_daily_reaction_limit_exists",
        "test_get_user_reactions_has_default_limit_not_daily",
    ],
    # Tests existentes críticos del proyecto
    "tests/integration/test_vip_flow.py": [
        "test_complete_vip_flow",
        "test_token_expiration_flow",
        "test_subscription_expiration_detection",
        "test_reminder_system_flow",
    ],
    # test_free_entry_flow.py covered via -k in CI; no stale "test_free_channel_delayed_approval" (obsolete per review Issue 17; removed to avoid dangling).
}


# Colores para output
class Colors:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")


def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.END}")


def get_test_count():
    """Cuenta el total de tests críticos."""
    total = 0
    for tests in CRITICAL_TESTS.values():
        total += len(tests)
    return total


def list_tests():
    """Lista todos los tests críticos sin ejecutar."""
    print_header("TESTS CRÍTICOS CONFIGURADOS")

    total_tests = get_test_count()
    print(f"{Colors.BOLD}Total: {total_tests} tests críticos{Colors.END}\n")

    for test_file, tests in CRITICAL_TESTS.items():
        print(f"{Colors.BOLD}{test_file}:{Colors.END}")
        for test in tests:
            print(f"  • {test}")
        print()


def run_critical_tests() -> dict:
    """Ejecuta todos los tests críticos y retorna resultados."""
    print_header("EJECUTANDO TESTS CRÍTICOS")

    start_time = datetime.now()

    # Cambiar al directorio del proyecto
    project_root = Path(__file__).parent
    os.chdir(project_root)

    test_files = list(CRITICAL_TESTS.keys())

    print(f"{Colors.BLUE}Ejecutando {get_test_count()} tests críticos...{Colors.END}")
    print(f"{Colors.BLUE}Archivos: {len(test_files)}{Colors.END}\n")

    # Ejecutar pytest directamente con los archivos
    result = subprocess.run(
        ["python", "-m", "pytest"] + test_files + ["-v", "--tb=short", "--no-cov", "--color=yes"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )

    output = result.stdout + result.stderr

    # Parsear resultados
    results = {
        "passed": 0,
        "failed": 0,
        "total": 0,
        "passed_tests": [],
        "failed_tests": [],
        "errors": [],
        "duration": 0,
    }

    # Extraer resumen del output
    for line in output.split("\n"):
        if "passed" in line.lower():
            # Buscar patrón como "13 passed"
            import re

            match = re.search(r"(\d+)\s+passed", line)
            if match:
                results["passed"] = int(match.group(1))
            match = re.search(r"(\d+)\s+failed", line)
            if match:
                results["failed"] = int(match.group(1))

        # Extraer nombres de tests
        if "PASSED" in line:
            parts = line.split("::")
            if len(parts) > 1:
                test_name = parts[-1].split()[0]
                results["passed_tests"].append(test_name)
        elif "FAILED" in line:
            parts = line.split("::")
            if len(parts) > 1:
                test_name = parts[-1].split()[0]
                results["failed_tests"].append(test_name)

    results["total"] = results["passed"] + results["failed"]
    results["duration"] = (datetime.now() - start_time).total_seconds()

    # Guardar output completo para debugging
    results["output"] = output[:2000] if len(output) > 2000 else output

    return results


def print_results(results: dict):
    """Imprime los resultados de forma clara."""
    print_header("RESULTADOS")

    passed = results.get("passed", 0)
    failed = results.get("failed", 0)
    total = results.get("total", passed + failed)

    print(f"{Colors.BOLD}Total ejecutados: {total}{Colors.END}")
    print(f"{Colors.GREEN}✓ Pasados:     {passed}{Colors.END}")
    print(f"{Colors.RED}✗ Fallidos:    {failed}{Colors.END}")

    if "duration" in results:
        print(f"{Colors.BLUE}⏱ Duración:   {results['duration']:.2f}s{Colors.END}")

    print()

    # Tests fallidos
    if results.get("failed_tests"):
        print(f"{Colors.BOLD}{Colors.RED}Tests fallidos:{Colors.END}")
        for test in results["failed_tests"]:
            print(f"  ✗ {test}")
        print()

    # Estado final
    if failed == 0:
        print_success(f"Todos los tests críticos pasaron ({passed}/{passed})")
        return True
    else:
        print_error(f"{failed} test(s) crítico(s) falló/fallaron")
        # Mostrar output si hay errores
        if results.get("output"):
            print(f"\n{Colors.YELLOW}Output (últimas líneas):{Colors.END}")
            print("\n".join(results["output"].split("\n")[-10:]))
        return False


def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--list":
            list_tests()
            return 0
        elif sys.argv[1] == "--help":
            print(__doc__)
            return 0

    # Ejecutar tests
    results = run_critical_tests()
    success = print_results(results)

    # Guardar resultados para referencia
    stats_file = Path(__file__).parent / ".critical_tests_stats.json"
    with open(stats_file, "w") as f:
        json.dump(results, f, indent=2)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
