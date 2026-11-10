#!/usr/bin/env python3
"""Lot 07 — Commande unique : refait tout depuis le brut.

Usage (depuis near-thesis/, ou depuis n'importe ou) :
    python rebuild.py
    python rebuild.py --skip-fetch       # 100 % cache : data/raw/ existant
    python rebuild.py --start-date 2026-10-01
    python rebuild.py --skip-charts --skip-dashboard

Etapes :
  1. fetch-bigquery (scripts/fetch_bigquery.py). Exit 2 (pas de credentials)
     ou script absent => mode cache : on reutilise data/raw/bq_*.csv.
  2. fetch-intents (scripts/fetch_intents.py). Exit 2 (pas de JWT) ou script
     absent => mode cache : on reutilise data/raw/intents_*.json.
  3. merge (scripts/merge_daily.py) => data/merged/daily.csv. Obligatoire.
  4. charts : scripts/build_charts.py si present, sinon chaque
     scripts/chart_*.py present (lots 08-11). cwd = near-thesis/.
  5. dashboard : scripts/build_dashboard.py si present (lot 12).

Idempotent : le merge est deterministe (tri par date, dedup, ecriture
atomique) ; relancer rebuild sur le meme brut produit le meme daily.csv.
Exit non-zero si data/merged/daily.csv est absent a la fin.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT / "scripts"
RAW_DIR = ROOT / "data" / "raw"
DAILY_CSV = ROOT / "data" / "merged" / "daily.csv"
START_DATE_DEFAULT = "2026-10-01"


def _log(msg: str) -> None:
    print(msg, flush=True)


def run(cmd: list[str], step: str) -> int:
    """Execute une etape (cwd = near-thesis/), sortie en direct."""
    _log(f"--- {step} : {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, cwd=ROOT)
    except OSError as exc:
        _log(f"[echec] {step} : execution impossible ({exc})")
        return 127
    if proc.returncode == 0:
        _log(f"[ok] {step}")
    else:
        _log(f"[echec] {step} : exit {proc.returncode}")
    return proc.returncode


def cache_status(pattern: str) -> str:
    files = sorted(RAW_DIR.glob(pattern)) if RAW_DIR.is_dir() else []
    if not files:
        return "aucun fichier en cache"
    return f"{len(files)} fichier(s) en cache ({files[0].name}...)" if len(files) > 1 \
        else f"1 fichier en cache ({files[0].name})"


def step_fetch_bigquery(start_date: str, errors: list[str]) -> None:
    _log("=== [1/5] fetch-bigquery ===")
    script = SCRIPTS / "fetch_bigquery.py"
    if not script.is_file():
        _log("[cache] scripts/fetch_bigquery.py absent (lot 05 non livre ?) : "
             f"on reutilise le brut ({cache_status('bq_*.csv')}).")
        return
    code = run([sys.executable, "scripts/fetch_bigquery.py",
                "--start-date", start_date], "fetch-bigquery")
    if code == 0:
        return
    if code == 2:
        _log("[cache] BigQuery sans credentials (exit 2) : "
             f"on reutilise le brut ({cache_status('bq_*.csv')}).")
        return
    _log(f"[warn] fetch-bigquery exit {code} : on continue sur le cache "
         f"({cache_status('bq_*.csv')}).")
    errors.append(f"fetch-bigquery exit {code}")


def step_fetch_intents(start_date: str, errors: list[str]) -> None:
    _log("=== [2/5] fetch-intents ===")
    script = SCRIPTS / "fetch_intents.py"
    if not script.is_file():
        _log("[cache] scripts/fetch_intents.py absent (lot 06 non livre ?) : "
             f"on reutilise le brut ({cache_status('intents_*.json')}).")
        return
    code = run([sys.executable, "scripts/fetch_intents.py",
                "--start", start_date], "fetch-intents")
    if code == 0:
        return
    if code == 2:
        _log("[cache] Intents sans JWT (exit 2) : "
             f"on reutilise le brut ({cache_status('intents_*.json')}). "
             "Memes chiffres qu'un pull frais sur la meme fenetre.")
        return
    _log(f"[warn] fetch-intents exit {code} : on continue sur le cache "
         f"({cache_status('intents_*.json')}).")
    errors.append(f"fetch-intents exit {code}")


def step_merge(errors: list[str]) -> bool:
    _log("=== [3/5] merge ===")
    script = SCRIPTS / "merge_daily.py"
    if not script.is_file():
        errors.append("scripts/merge_daily.py absent")
        _log("[echec] scripts/merge_daily.py absent : impossible de produire "
             "data/merged/daily.csv.")
        return False
    code = run([sys.executable, "scripts/merge_daily.py"], "merge")
    if code != 0:
        errors.append(f"merge exit {code}")
        return False
    return True


def step_charts(errors: list[str]) -> None:
    _log("=== [4/5] charts ===")
    bundle = SCRIPTS / "build_charts.py"
    if bundle.is_file():
        code = run([sys.executable, "scripts/build_charts.py"], "build_charts")
        if code != 0:
            errors.append(f"build_charts exit {code}")
        return
    charts = sorted(SCRIPTS.glob("chart_*.py"))
    if not charts:
        _log("[warn] aucun script chart (ni build_charts.py ni chart_*.py, "
             "lots 08-11 non livres ?) : etape sautee.")
        return
    for chart in charts:
        code = run([sys.executable, f"scripts/{chart.name}"], chart.stem)
        if code != 0:
            errors.append(f"{chart.name} exit {code}")


def step_dashboard(errors: list[str]) -> None:
    _log("=== [5/5] dashboard ===")
    script = SCRIPTS / "build_dashboard.py"
    if not script.is_file():
        _log("[warn] scripts/build_dashboard.py absent (lot 12 non livre ?) : "
             "etape sautee.")
        return
    code = run([sys.executable, "scripts/build_dashboard.py"], "build_dashboard")
    if code != 0:
        errors.append(f"build_dashboard exit {code}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Rebuild unique near-thesis : fetch -> merge -> charts -> dashboard.")
    p.add_argument("--start-date", default=START_DATE_DEFAULT,
                   help=f"Debut de fenetre (defaut : {START_DATE_DEFAULT}).")
    p.add_argument("--skip-fetch", action="store_true",
                   help="Saute les pulls reseau : 100 %% cache data/raw/.")
    p.add_argument("--skip-charts", action="store_true",
                   help="Saute l'etape charts.")
    p.add_argument("--skip-dashboard", action="store_true",
                   help="Saute l'etape dashboard.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    errors: list[str] = []
    _log(f"[rebuild] racine={ROOT} start_date={args.start_date} "
          f"skip_fetch={args.skip_fetch}")

    if args.skip_fetch:
        _log("=== [1-2/5] fetch : sautes (--skip-fetch, 100 % cache) ===")
        _log(f"  bq : {cache_status('bq_*.csv')}")
        _log(f"  intents : {cache_status('intents_*.json')}")
    else:
        step_fetch_bigquery(args.start_date, errors)
        step_fetch_intents(args.start_date, errors)

    merge_ok = step_merge(errors)

    if not DAILY_CSV.is_file():
        _log(f"[FATAL] {DAILY_CSV} absent : rebuild impossible. "
             "Verifiez data/raw/ (pulls ou cache) puis relancez.")
        errors.append("data/merged/daily.csv absent")
    elif merge_ok:
        if args.skip_charts:
            _log("=== [4/5] charts : sautes (--skip-charts) ===")
        else:
            step_charts(errors)
        if args.skip_dashboard:
            _log("=== [5/5] dashboard : sautes (--skip-dashboard) ===")
        else:
            step_dashboard(errors)
    else:
        _log("[warn] merge en echec : charts/dashboard sautes pour ne pas "
             "figer des chiffres perimes.")

    _log("=== resume ===")
    _log(f"  daily.csv : {'present' if DAILY_CSV.is_file() else 'ABSENT'} "
         f"({DAILY_CSV})")
    if errors:
        _log(f"  {len(errors)} probleme(s) :")
        for err in errors:
            _log(f"    - {err}")
        _log("[REBUILD ECHEC]")
        return 1
    _log("[REBUILD OK]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
