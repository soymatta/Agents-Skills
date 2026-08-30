#!/usr/bin/env python3
"""
verify_ai.py — Free AI-detection pipeline (no paid APIs).

Combines up to four free layers into one gate:

  Layer 1  Lingüística (local, instantánea, funciona en español)
           burstiness (SD de longitud de frases), variedad léxica (TTR),
           densidad de conectores, frases AI (tabla del content-humanizer),
           ratio heurístico de pasiva, puntuación natural (; : — ()).

  Layer 2  Detectores neuronales LOCALES (HuggingFace, en tu máquina,
           caché en HF_HOME, habitualmente .venv/hf_cache -> gitignored)
           - roberta-base-openai-detector  (por defecto)
           - modelo(s) extra con --local-extra, p. ej.
             Radix/detect-ai-text  o  Hello-SimpleAI/HC3-Detector
             (si un id no existe o está gated, se salta con aviso)

  Layer 3  Hugging Face Inference API (GRATIS, requiere tu HF_TOKEN)
           - detector por texto (--hf-token model por defecto
             Radix/detect-ai-text; si el endpoint no lo sirve, salta)
           - juez LLM opcional --hf-judge (p. ej. mistralai/...)

  Layer 4  GPTZero API (plan gratuito con créditos limitados) si existe
           GPTZERO_API_KEY (endpoint oficial de pago con tier gratis;
           no se hace scraping de su web interactiva)

Fusión:  local = media(local detectors)
         externa = media(HF detector, GPTZero disponibles)
         final = 0.6*local + 0.4*externa   (si no hay externa -> local)
gate:    global <= umbral  Y  ninguna sección > umbral  =>  exit 0 (PASA)
         usa --threshold 0.5 por defecto.

Uso:
    python verify_ai.py --file documento.md [--threshold 0.5] [--verbose]
    python verify_ai.py --file documento.md --local-extra        # más detectores locales
    python verify_ai.py --file documento.md --hf-token $HF_TOKEN
    python verify_ai.py --file documento.md --hf-token ... --hf-judge
    python verify_ai.py --file documento.md --gptzero-key ...    # o env GPTZERO_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── Texto / ventanas ─────────────────────────────────────────────────────────

LIMIT512 = 880  # RoBERTa acepta 512 tokens; margen para español multi-token


def chunk_text(text: str, size: int = LIMIT512) -> list[str]:
    return [text[i : i + size] for i in range(0, len(text), size)]


def sentence_lengths(text: str) -> list[int]:
    parts = re.split(r"[.!?]+", text)
    return [len([w for w in p.split() if w]) for p in parts if p.strip()]


# ── Capa 1: lingüística ──────────────────────────────────────────────────────

CONNECTORS_ES = [
    "además", "asimismo", "sin embargo", "por tanto", "por lo tanto", "en cambio",
    "por otro lado", "no solo", "cabe destacar", "cabe resaltar", "conviene señalar",
    "en este sentido", "por ejemplo", "finalmente", "en primer lugar",
    "en segundo lugar", "en tercer lugar", "con respecto a", "en relación con",
    "es evidente", "es importante", "es fundamental", "se puede observar",
]

CONNECTORS_EN = [
    "moreover", "furthermore", "however", "therefore", "in addition",
    "in this regard", "it is important", "it is worth", "it should be noted",
]

AI_PHRASES = CONNECTORS_ES + CONNECTORS_EN


def linguistic_analysis(text: str) -> dict:
    low = text.lower()
    lens = sentence_lengths(text)
    words = [w for w in re.split(r"\W+", low) if w]
    total_words = len(words)
    unique = len(set(words))
    n_sent = max(len(lens), 1)

    phrase_hits = {p: len(re.findall(re.escape(p), low)) for p in AI_PHRASES}
    phrase_total = sum(phrase_hits.values())

    # Heurística de pasiva (aproximada): se/es/son/fue + participio (-ado/-ido/-ed)
    passive = len(re.findall(
        r"\b(?:se|es|son|fue|fueron|han sido|ha sido|is|are|was|were|been|"
        r"has been|have been)\s+\w+(?:ado|ada|ido|ida|ados|adas|idos|idas|ed|en)\b",
        low,
    ))

    natural_punct = {
        ";": low.count(";"),
        ":": low.count(":"),
        "—": low.count("—"),
        "()": len(re.findall(r"\([^)]*\)", text)),
    }

    stats = {}
    if len(lens) > 1:
        stats["mean"] = round(statistics.mean(lens), 1)
        stats["sd"] = round(statistics.stdev(lens), 1)
    else:
        stats["mean"] = round(statistics.mean(lens), 1) if lens else 0.0
        stats["sd"] = 0.0
    stats["short_lt15"] = sum(1 for x in lens if x < 15)
    stats["long_gt25"] = sum(1 for x in lens if x > 25)

    return {
        "sentences": len(lens),
        "words": total_words,
        "mean_len": stats["mean"],
        "burstiness_sd": stats["sd"],
        "short_lt15": stats["short_lt15"],
        "long_gt25": stats["long_gt25"],
        "ttr": round(unique / total_words, 3) if total_words else 0.0,
        "connector_density": round(phrase_total / n_sent, 2),
        "top_phrases": sorted(
            ((p, c) for p, c in phrase_hits.items() if c > 0),
            key=lambda x: -x[1],
        )[:6],
        "passive_per_sent": round(passive / n_sent, 2),
        "punct": natural_punct,
    }


# ── Capa 2: detectores locales ───────────────────────────────────────────────

LOCAL_EXTRA = [
    "Radix/detect-ai-text",
    "Hello-SimpleAI/HC3-Detector",
]


def _classify_chunks(detect, chunks: list[str]) -> dict:
    ai = 0.0
    human = 0.0
    for c in chunks:
        try:
            res = detect(c)
        except Exception:
            continue
        for entry in res[0]:
            lab = entry["label"].upper()
            if lab in ("FAKE", "AI", "AI-GENERATED", "LABEL_1"):
                ai += entry["score"]
            elif lab in ("REAL", "HUMAN", "LABEL_0"):
                human += entry["score"]
    n = len(chunks)
    if not n:
        return {"ai_prob": 0.0, "human_prob": 0.0, "label": "n/a"}
    ai = round(ai / n, 4)
    human = round(human / n, 4)
    return {"ai_prob": ai, "human_prob": human, "label": "AI" if ai > human else "HUMAN"}


_ROBERTA = {"pipe": None}


def get_roberta(hf_home: str):
    if _ROBERTA["pipe"] is None:
        import os as _os

        _os.environ.setdefault("HF_HOME", hf_home)
        from transformers import pipeline

        _ROBERTA["pipe"] = pipeline(
            "text-classification",
            model="openai-community/roberta-base-openai-detector",
            top_k=None,
        )
    return _ROBERTA["pipe"]


def local_detection(text: str, hf_home: str, include_extra: bool) -> dict:
    """RoBERTa (siempre) + detectores extra locales opcionales."""
    chunks = chunk_text(text)
    out = {"roberta": None, "extra": {}}
    try:
        roberta = get_roberta(hf_home)
        out["roberta"] = _classify_chunks(roberta, chunks)
    except Exception as exc:  # noqa: BLE001
        out["roberta_error"] = str(exc)[:200]

    if include_extra:
        from transformers import pipeline as _pipe  # noqa: F401

        for model_id in LOCAL_EXTRA:
            try:
                det = _pipe("text-classification", model=model_id, top_k=None)
                out["extra"][model_id] = _classify_chunks(det, chunks)
            except Exception as exc:  # noqa: BLE001
                out["extra"][model_id] = {"error": str(exc)[:200]}
    return out


# ── Capa 3 + 4: servicios externos gratuitos ─────────────────────────────────

def _hf_request(model: str, payload: dict, token: str, timeout: int = 60) -> dict | None:
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200] if e.fp else str(e)
        return {"error": f"HTTP {e.code}: {body}"}
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:200]}


def hf_detector(text: str, token: str, model: str, max_requests: int = 6) -> dict:
    """Inference API de HF (gratis): text-classification por ventanas acotadas."""
    findings = []
    for c in chunk_text(text)[:max_requests]:
        res = _hf_request(model, {"inputs": c, "parameters": {"wait_for_model": True}}, token)
        if not isinstance(res, list) or not res:
            return {"model": model, "error": res.get("error", "respuesta no válida") if isinstance(res, dict) else "?",
                    "ai_prob": None}
        ai = 0.0
        for entry in res[0]:
            lab = entry.get("label", "").upper()
            if lab in ("FAKE", "AI", "AI-GENERATED", "LABEL_1"):
                ai = entry.get("score", 0.0)
        findings.append(ai)
    return {"model": model, "ai_prob": round(sum(findings) / len(findings), 4)}


def hf_judge(text: str, token: str, model: str) -> dict:
    """Juez LLM gratuito vía Inference API: devuelve P(IA) 0-1 parseando la respuesta."""
    prompt = (
        "Eres un evaluador de texto académico. El siguiente fragmento "
        "¿fue escrito por un humano o generado por IA? "
        "Responde SOLO con un número entre 0 y 1 que sea la probabilidad de IA.\n\n"
        f"{text[:4000]}\n\nProbabilidad de IA (0-1):"
    )
    res = _hf_request(
        model,
        {"inputs": prompt, "parameters": {"max_new_tokens": 12, "wait_for_model": True}},
        token,
    )
    if isinstance(res, dict) and "error" in res:
        return {"model": model, "error": res["error"], "ai_prob": None}
    outputs = res if isinstance(res, list) else res.get("generated_text", [])
    gen = ""
    if isinstance(outputs, list):
        for o in outputs:
            if isinstance(o, dict) and o.get("generated_text"):
                gen += o["generated_text"]
    elif isinstance(outputs, str):
        gen = outputs
    matches = re.findall(r"(0\.\d+|1\.0+|0|1)\b", gen)
    if matches:
        val = float(matches[-1])
        return {"model": model, "ai_prob": round(min(val, 1.0), 4)}
    return {"model": model, "error": f"sin número en respuesta: {gen[:120]}", "ai_prob": None}


GPTZERO_URL = "https://api.gptzero.me/v2/predict/text"


def gptzero(text: str, key: str, max_requests: int = 3) -> dict:
    """GPTZero API (tier gratis): predecir por trozos de <=4000 caracteres."""
    data = {"document": text[:4000], "version": "2024-11-01"}
    headers = {"X-API-KEY": key, "Content-Type": "application/json"}
    req = urllib.request.Request(
        GPTZERO_URL, data=json.dumps(data).encode(), headers=headers
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.loads(r.read().decode())
    except Exception as e:  # noqa: BLE001
        return {"ai_prob": None, "error": str(e)[:200]}

    docs = res.get("documents") or []
    if not docs:
        return {"ai_prob": None, "error": "sin documents en respuesta"}
    d = docs[0]
    rg = d.get("result_gptzero") or {}
    if isinstance(rg, dict):
        prob = rg.get("probability")
        label = rg.get("ai")
        return {
            "ai_prob": round(float(prob or 0.0), 4) if prob is not None else None,
            "class": label,
        }
    clazz = str(d.get("class", "")).lower()
    mapping = {"ai": 0.9, "mixed": 0.5, "human": 0.08}
    return {"ai_prob": mapping.get(clazz), "class": clazz}


# ── Reporte ───────────────────────────────────────────────────────────────────


def human_path(text: str) -> dict:
    m = linguistic_analysis(text)
    return {
        "burstiness_sd": m["burstiness_sd"],
        "mean_len": m["mean_len"],
        "sentences": m["sentences"],
        "words": m["words"],
        "ttr": m["ttr"],
        "short_lt15": m["short_lt15"],
        "long_gt25": m["long_gt25"],
        "connector_density": m["connector_density"],
        "top_phrases": m["top_phrases"],
        "passive_per_sent": m["passive_per_sent"],
        "punct": m["punct"],
    }


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

    ap = argparse.ArgumentParser(description="Pipeline gratuito de detección de IA")
    ap.add_argument("--file", "-f", required=True)
    ap.add_argument("--threshold", "-t", type=float, default=0.5)
    ap.add_argument("--verbose", "-v", action="store_true")
    ap.add_argument("--local-extra", action="store_true", help="detectores HF locales extra")
    ap.add_argument("--no-local", action="store_true")
    ap.add_argument("--no-external", action="store_true")
    ap.add_argument("--hf-token", default=os.environ.get("HF_TOKEN", ""))
    ap.add_argument("--hf-detector", default="Radix/detect-ai-text")
    ap.add_argument("--hf-judge", default="mistralai/Mistral-7B-Instruct-v0.2")
    ap.add_argument("--gptzero-key", default=os.environ.get("GPTZERO_API_KEY", ""))
    args = ap.parse_args()

    text = Path(args.file).read_text(encoding="utf-8")
    if not text.strip():
        print("Error: texto vacío.")
        return 1

    sections = []
    lines = text.split("\n")
    cur = "INICIO"
    body: list[str] = []
    for ln in lines:
        if re.match(r"^#{1,4}\s", ln):
            if "".join(body).strip():
                sections.append((cur, "\n".join(body)))
            cur = ln.strip().lstrip("#").strip()
            body = []
        else:
            body.append(ln)
    if "".join(body).strip():
        sections.append((cur, "\n".join(body)))

    # ── Local ─────────────────────────────────────────────────────────────
    hf_home = os.environ.get("HF_HOME", os.path.join(os.path.dirname(__file__), "..", ".models"))
    local = {"roberta": None, "extra": {}, "error": None}
    if not args.no_local:
        local = local_detection(text, hf_home, args.local_extra)

    # ── Externas ──────────────────────────────────────────────────────────
    ext = []
    if not args.no_external:
        if args.hf_token:
            r = hf_detector(text, args.hf_token, args.hf_detector)
            ext.append(("hf-detector", r))
            r = hf_judge(text, args.hf_token, args.hf_judge)
            ext.append(("hf-judge", r))
        if args.gptzero_key:
            ext.append(("gptzero", gptzero(text, args.gptzero_key)))

    # ── Fusión / gate ─────────────────────────────────────────────────────
    roberta_ai = (local.get("roberta") or {}).get("ai_prob") if local.get("roberta") else None
    extra_ais = [
        v["ai_prob"]
        for k, v in (local.get("extra") or {}).items()
        if isinstance(v, dict) and v.get("ai_prob") is not None
    ]
    local_vals = [x for x in ([roberta_ai] + extra_ais) if x is not None]
    local_ai = round(sum(local_vals) / len(local_vals), 4) if local_vals else None

    ext_vals = [r["ai_prob"] for n, r in ext if r.get("ai_prob") is not None]
    ext_ai = round(sum(ext_vals) / len(ext_vals), 4) if ext_vals else None

    if local_ai is not None and ext_ai is not None:
        fused = round(0.6 * local_ai + 0.4 * ext_ai, 4)
    elif local_ai is not None:
        fused = local_ai
    elif ext_ai is not None:
        fused = ext_ai
    else:
        fused = None

    bad_sections = []
    sec_rows = []
    roberta_pipe = None
    if not args.no_local:
        try:
            roberta_pipe = get_roberta(hf_home)
        except Exception:  # noqa: BLE001
            roberta_pipe = None
    for hdr, sec in sections:
        if len("".join(sec).split()) < 25:
            continue
        lm = human_path(sec)
        lai = None
        if roberta_pipe is not None:
            lai = _classify_chunks(roberta_pipe, chunk_text(sec))["ai_prob"]
        row = {
            "header": hdr[:50],
            "local": lai,
            "human": lm,
        }
        sec_rows.append(row)
        if lai is not None and lai > args.threshold:
            bad_sections.append((hdr, lai))

    # ── Impresión ─────────────────────────────────────────────────────────
    print("=" * 62)
    print("  PIPELINE GRATUITO DE DETECCIÓN DE IA")
    print("=" * 62)
    print(f"  Umbral: {args.threshold:.0%}")
    print()
    print("  --- Capa 1: métricas lingüísticas ---")
    g = human_path(text)
    print(f"  Frases: {g['sentences']}  Palabras: {g['words']}  "
          f"Longitud media: {g['mean_len']}  Burstiness SD: {g['burstiness_sd']} (>12 humano)")
    print(f"  TTR (diversidad léxica): {g['ttr']}  "
          f"Frases cortas(<15): {g['short_lt15']}  Largas(>25): {g['long_gt25']}")
    print(f"  Conectores/frase: {g['connector_density']}  "
          f"Pasivas/frase: {g['passive_per_sent']}  "
          f"Puntuación natural ;:{g['punct'][';']} :{g['punct'][':']} —:{g['punct']['—']}")
    if g["top_phrases"]:
        print("  Frases AI detectadas:", ", ".join(f'{p}(x{c})' for p, c in g["top_phrases"]))

    print()
    print("  --- Capa 2: detectores locales ---")
    if roberta_ai is not None:
        print(f"  roberta-base-openai-detector:  AI={roberta_ai:.1%}")
    for model_id, res in (local.get("extra") or {}).items():
        if isinstance(res, dict) and "error" in res:
            print(f"  {model_id}: NO DISPONIBLE ({res['error'][:60]})")
        else:
            print(f"  {model_id}: AI={(res or {}).get('ai_prob', 0):.1%}")

    print()
    print("  --- Capa 3+4: servicios externos gratuitos ---")
    if not ext and not args.no_external:
        print("  (sin HF_TOKEN ni GPTZERO_API_KEY — se omitió. Para activarlos:")
        print("   verify_ai.py --file X --hf-token $HF_TOKEN | --gptzero-key $GPTZERO_API_KEY)")
    for name, r in ext:
        if r.get("error"):
            print(f"  {name}: ERROR ({r['error'][:70]})")
        else:
            print(f"  {name}: AI={r.get('ai_prob'):.1%}")

    print()
    print("  --- Veredicto ---")
    if local_ai is not None and ext_ai is None:
        print(f"  Local AI = {local_ai:.1%}   (sin fuentes externas)")
    elif local_ai is not None and ext_ai is not None:
        print(f"  Local: {local_ai:.1%}   Ext.: {ext_ai:.1%}   FUSION = {fused:.1%}")
    elif ext_ai is not None and local_ai is None:
        print(f"  Ext.: {ext_ai:.1%} (local desactivado)")
    else:
        print("  ERROR: no se pudo obtener ninguna puntuación.")
        return 1

    if args.verbose:
        print()
        print("  --- Por sección (roberta local) ---")
        for row in sec_rows:
            lai = row["local"]
            icon = "PASA" if (lai is None or lai <= args.threshold) else "DETECTADO"
            st = f"[{icon}] {row['header']:<48} AI={lai:.1%}" if lai is not None else f"[n/a] {row['header']}"
            print("  " + st)

    if bad_sections:
        worst = max(bad_sections, key=lambda x: x[1])
        print(f"\n  Sección con mayor puntaje AI: \"{worst[0]}\" ({worst[1]:.1%})")
        print("  >> content-humanizer: repasar las secciones señaladas.")

    verdict = "PASA"
    if fused is None:
        verdict = "ERROR"
    elif fused > args.threshold or bad_sections:
        verdict = "DETECTADO"

    print()
    print("=" * 62)
    print(f"  AI:   {(fused or 0.0):.1%}   Human: {(1-(fused or 0.0)):.1%}")
    print(f"  Verdict: {verdict}")
    print("=" * 62)
    return 0 if verdict == "PASA" else 1


if __name__ == "__main__":
    raise SystemExit(main())