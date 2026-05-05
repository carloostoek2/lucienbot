#!/usr/bin/env python3
"""Cuenta preguntas en un archivo JSON de trivia."""

import json
import sys


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "preguntas.json"
    with open(path) as f:
        data = json.load(f)

    print(f"Total de preguntas: {len(data)}")
    for i, item in enumerate(data, 1):
        pregunta = item.get("q", "")[:50]
        respuesta = item.get("answer")
        print(f"  {i}. {pregunta}... → índice {respuesta}")


if __name__ == "__main__":
    main()