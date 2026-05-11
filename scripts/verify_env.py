#!/usr/bin/env python3
"""Verifica que todo esté instalado correctamente"""

import sys

required_packages = [
    'aiogram',
    'pytest',
    'pytest_asyncio',
    'ruff',
    'mypy',
    'pre_commit',
    'bandit',
    'safety',
    'freezegun',
    'rich'
]

print("🔍 Verificando entorno de desarrollo...\n")

missing = []
for package in required_packages:
    try:
        __import__(package.replace('-', '_'))
        print(f"✅ {package}")
    except ImportError:
        print(f"❌ {package} - NO INSTALADO")
        missing.append(package)

if missing:
    print(f"\n⚠️  Faltan instalar: {', '.join(missing)}")
    print("Ejecuta: pip install -r requirements-dev.txt")
    sys.exit(1)

print("\n🎉 ¡Todo listo para desarrollar!")