#!/usr/bin/env python3
"""
Detect AI-generated text using open-source models.

Analiza un archivo Markdown o texto y devuelve la probabilidad
de que haya sido generado por inteligencia artificial.

Usage:
    echo "text" | python detect_ai.py
    python detect_ai.py --file documento.md
    python detect_ai.py --file documento.md --verbose

Modelo: openai-community/roberta-base-openai-detector
Requiere: pip install transformers torch
"""

from __future__ import annotations

import argparse
import sys
import re
from pathlib import Path

# ── Detector ─────────────────────────────────────────────────────────────────


def load_detector():
    """Cargar modelo de deteccion. Retorna pipeline o None si no hay dependencias."""
    try:
        from transformers import pipeline
        return pipeline(
            "text-classification",
            model="openai-community/roberta-base-openai-detector",
            top_k=None,
        )
    except ImportError:
        return None


# ── Texto ────────────────────────────────────────────────────────────────────


def read_text(file_path: str | None) -> str:
    """Leer texto desde archivo o stdin."""
    if file_path:
        return Path(file_path).read_text(encoding="utf-8")
    return sys.stdin.read()


def split_sections(text: str, max_chars: int = 3000) -> list[tuple[str, str]]:
    """Dividir texto en secciones (por headers) para analisis granular."""
    sections = []
    lines = text.split("\n")
    current: list[str] = []
    current_header = "INICIO"

    for line in lines:
        if re.match(r"^#{1,4}\s", line):
            if current:
                sections.append((current_header, "\n".join(current)))
            current_header = line.strip().lstrip("#").strip()
            current = []
        else:
            current.append(line)

    if current:
        sections.append((current_header, "\n".join(current)))

    # Fusionar secciones pequeñas
    merged: list[tuple[str, str]] = []
    buf_header = ""
    buf_text = ""
    for header, body in sections:
        if len(buf_text) + len(body) < max_chars and buf_text:
            buf_text += "\n" + body
        else:
            if buf_text:
                merged.append((buf_header, buf_text))
            buf_header = header
            buf_text = body
    if buf_text:
        merged.append((buf_header, buf_text))

    return merged


# ── Analisis ─────────────────────────────────────────────────────────────────


def classify_section(detector, text: str) -> dict:
    """Clasificar un fragmento de texto."""
    if not text.strip():
        return {"label": "SKIP", "score": 0.0, "ai_prob": 0.0, "human_prob": 0.0}

    # Truncar a 512 tokens (limite del modelo)
    truncated = text[:2000]
    result = detector(truncated)

    ai_prob = 0.0
    human_prob = 0.0
    label = "UNKNOWN"
    for entry in result[0]:
        if entry["label"].upper() in ("FAKE", "AI", "AI-GENERATED", "LABEL_1"):
            ai_prob = entry["score"]
        elif entry["label"].upper() in ("REAL", "HUMAN", "LABEL_0"):
            human_prob = entry["score"]

    if ai_prob > human_prob:
        label = "AI"
    else:
        label = "HUMAN"

    return {"label": label, "ai_prob": round(ai_prob, 4), "human_prob": round(human_prob, 4)}


# ── Output ───────────────────────────────────────────────────────────────────


def print_result(global_result: dict, section_results: list[dict], verbose: bool):
    """Imprimir resultados."""
    ai = global_result["ai_prob"]
    human = global_result["human_prob"]

    verdict = "PASA" if global_result["label"] == "HUMAN" else "DETECTADO"

    print(f"\n{'=' * 50}")
    print(f"  DETECTOR DE IA — Resultados")
    print(f"{'=' * 50}")
    print(f"  AI:   {ai:.1%}")
    print(f"  Human: {human:.1%}")
    print(f"  Verdict: {verdict}")
    print(f"{'=' * 50}")

    if global_result["label"] == "AI":
        print(f"  >> El texto probablemente fue generado por IA.")
        print(f"  >> Ejecuta content-humanizer nuevamente.")
    else:
        print(f"  >> El texto pasa como escrito por humano.")

    if verbose and section_results:
        print(f"\n{'─' * 50}")
        print(f"  ANALISIS POR SECCION")
        print(f"{'─' * 50}")
        for sec in section_results:
            icon = "PASA" if sec["label"] == "HUMAN" else "!! "
            print(f"  [{icon}] {sec['header']}: AI={sec['ai_prob']:.1%}")
        print(f"{'─' * 50}")

    if verbose and global_result["label"] == "AI":
        worst = max(section_results, key=lambda s: s["ai_prob"])
        print(f"\n  Seccion con mayor puntaje AI: \"{worst['header']}\" ({worst['ai_prob']:.1%})")
        print(f"  Revisar: fragmentos de ~{worst['length']} caracteres\n")


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Detectar texto generado por IA")
    parser.add_argument("--file", "-f", help="Archivo a analizar")
    parser.add_argument("--verbose", "-v", action="store_true", help="Analisis por seccion")
    parser.add_argument("--threshold", "-t", type=float, default=0.5, help="Umbral AI (default: 0.5)")
    args = parser.parse_args()

    # Verificar dependencias
    detector = load_detector()
    if detector is None:
        print("\n  ERROR: transformers no instalado.")
        print("  Instalar con: pip install transformers torch")
        print("  O alternativamente, usar: pip install transformers tensorflow\n")
        return 1

    # Leer texto
    text = read_text(args.file)
    if not text.strip():
        print("  Error: texto vacio.")
        return 1

    # Analisis global
    global_result = classify_section(detector, text)

    # Analisis por seccion
    sections = split_sections(text)
    section_results = []
    for header, body in sections:
        if len(body.strip()) < 50:
            continue
        result = classify_section(detector, body)
        result["header"] = header
        result["length"] = len(body)
        section_results.append(result)

    # Determinar verdict final: si AI > threshold y ademas en global o en
    # cualquier seccion pasa el umbral
    final_label = global_result["label"]
    if global_result["ai_prob"] > args.threshold:
        final_label = "AI"
    elif any(s["label"] == "AI" for s in section_results):
        final_label = "AI"

    global_result["label"] = final_label

    # Print
    print_result(global_result, section_results, args.verbose)

    return 0 if final_label == "HUMAN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
