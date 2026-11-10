#!/usr/bin/env python3
"""Lot 12 — Genere le dashboard statique autonome (near-thesis/dashboard.html).

Conforme a near-thesis/docs/maquette.md (option A sobre academique) :
ordre des 5 blocs §2, gabarits de phrases §4 remplis par ce script depuis
data/merged/daily.csv + logs (jamais a la main), palette et CSS inline §5,
images PNG embarquees en base64, zero requete reseau, <details> fermes sauf
le verdict.

Orchestrateur (agents.md regle 2 : modules ≤ 500 lignes) :
- dashboard_content : textes, blocs, CSS ;
- dashboard_data : chargement des donnees reelles ;
- dashboard_phrases : phrases factuelles §4 ;
- dashboard_render : assemblage HTML.

Usage :
    python scripts/build_dashboard.py
    python scripts/build_dashboard.py --out dashboard.html

Entrees REQUISES (echec propre, exit 2, liste explicite si absentes) :
  - charts/01_actifs_intents.png (lot 08), charts/04_leadlag.png (lot 10),
    charts/02_tx.png + charts/03_contrats.png (lot 09, deux PNG),
    charts/05_concentration.png (lot 11). Noms constates dans les scripts
    chart_*.py livres (ne pas renommer sans eux).
    Note maquette : le bloc 3 embarque les 2 PNG du lot 09 (la maquette
    pre-lots supposait 1 PNG/lot) ; ordre, roles, details, phrases et
    lectures inchangees. Le bloc 5 n'a pas de PNG (tableau, §8 Q3).
  - data/merged/daily.csv (lot 07, contrat intent.md).
  - queries/00_sample.sql, 01_active_accounts.sql, 02_tx_counts.sql,
    03_contract_usage.sql, 04_top_contracts.sql (lus verbatim).

Entrees OPTIONNELLES (mention honnete « non releve / non calculable »,
jamais de chiffre invente) :
  - data/raw/bq_pull_log.jsonl + data/raw/bq_*.meta.json (lot 05 : pull
    BigQuery, bytes, MAX(block_date)) ; repli : data/logs/*.json, logs/*.json
    (cles reconnues : voir _BQ_PULL_KEYS / _BQ_BYTES_KEYS / _BQ_MAXBD_KEYS).
  - data/raw/intents_*.json (lot 06 : pull_date + volumes par portefeuille ;
    agregation alignee sur scripts/chart_concentration.py, lot 11).
  - data/merged/top_contracts.csv, sinon data/raw/bq_04_top_contracts.csv
    (sortie de 04_top_contracts.sql).
  - THESIS.md (lot 13) : lignes « Verdict: CONFIRME|NUANCE|INFIRME »,
    « Seuil: ... », « Phrase-verdict: ... » (premieres occurrences).

Regles de calcul (deterministes, documentees) : _trend_words (moities de
fenetre), _pearson (minimum 3 paires, None si serie constante),
TOP_K_WALLETS / TOP_K_CONTRACTS, MANY_FEW_THRESHOLD_PCT.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import sys
from pathlib import Path

try:
    from scripts.dashboard_content import (
        BLOCKS,
        CLAIM,
        PRICE_NOTE,
        TEXT_SOURCES,
    )
    from scripts.dashboard_data import (
        _load_bq_meta,
        _load_intents_raw,
        _load_top_contracts,
        _load_verdict,
        _read_daily,
        _resolve_top_contracts,
        _wallet_volumes,
    )
    from scripts.dashboard_phrases import _build_phrases, fmt_int
    from scripts.dashboard_render import _rel, build_html
except ImportError:  # execution directe : python scripts/xxx.py
    from dashboard_content import (
        BLOCKS,
        CLAIM,
        PRICE_NOTE,
        TEXT_SOURCES,
    )
    from dashboard_data import (
        _load_bq_meta,
        _load_intents_raw,
        _load_top_contracts,
        _load_verdict,
        _read_daily,
        _resolve_top_contracts,
        _wallet_volumes,
    )
    from dashboard_phrases import _build_phrases, fmt_int
    from dashboard_render import _rel, build_html

# Re-exporte pour compatibilite ascendante (import ... depuis ce module) :
# BLOCKS, CLAIM, PRICE_NOTE, TEXT_SOURCES, _read_daily, _load_bq_meta,
# _load_intents_raw, _load_top_contracts, _load_verdict,
# _resolve_top_contracts, _wallet_volumes, _build_phrases, fmt_int,
# _rel, build_html.


def _repo_root() -> Path:
    # scripts/build_dashboard.py -> near-thesis/
    return Path(__file__).resolve().parent.parent


def _check_png_files(charts_dir: Path) -> list[tuple[str, str, str]]:
    """Liste les PNG requis (blocs 1-4), echec explicite si absents."""
    need_png = [(png, b["id"], b["lot"]) for b in BLOCKS for png, _, _ in b["figures"]]
    missing_png = [
        f"charts/{png}  [bloc '{bid}', {lot}]"
        for png, bid, lot in need_png
        if not (charts_dir / png).is_file()
    ]
    if missing_png:
        raise FileNotFoundError(
            "PNG manquants (%d/%d) :\n  - %s\n"
            "Générez-les via les lots 08-11 (ou `python rebuild.py`), "
            "puis relancez ce script."
            % (len(missing_png), len(need_png), "\n  - ".join(missing_png))
        )
    return need_png


def _load_sql_texts(queries_dir: Path) -> dict[str, str]:
    """Lit les SQL requis verbatim, echec explicite si absents."""
    need_sql = sorted({ref for b in BLOCKS for kind, ref in b["sources"] if kind == "sql"})
    missing_sql = [f"queries/{f}" for f in need_sql if not (queries_dir / f).is_file()]
    if missing_sql:
        raise FileNotFoundError("Fichiers SQL manquants :\n  - " + "\n  - ".join(missing_sql))
    return {f: (queries_dir / f).read_text(encoding="utf-8") for f in need_sql}


def _build_details(
    queries_dir: Path, out_parent: Path, sql_text: dict[str, str]
) -> tuple[dict[str, list], dict[str, list]]:
    """Contenu des <details> (textes) + liens relatifs par bloc."""
    details: dict[str, list] = {}
    qlinks: dict[str, list] = {}
    for b in BLOCKS:
        blocs: list[tuple[str, str]] = []
        links: list[tuple[str, str]] = []
        for kind, ref in b["sources"]:
            if kind == "sql":
                blocs.append((f"Requête BigQuery exacte — queries/{ref}", sql_text[ref]))
                links.append((f"queries/{ref}", _rel(queries_dir / ref, out_parent)))
            else:
                if ref not in TEXT_SOURCES:
                    raise KeyError(f"Bloc '{b['id']}' : clé TEXT_SOURCES inconnue : {ref!r}.")
                blocs.append(TEXT_SOURCES[ref])
        details[b["id"]] = blocs
        qlinks[b["id"]] = links
    return details, qlinks


def _fresh_pulls(
    bq: dict[str, str | None], n_raw_files: int, intent_pull: str | None,
    daily: dict[str, list],
) -> tuple[str, str, str, list[tuple[str, str]]]:
    """Libelles de fraicheur + lignes du tableau methode."""
    n = len(daily["date"])
    dmin, dmax = daily["date"][0], daily["date"][-1]
    maxbd = bq["max_block_date"] or "non relevé (aucun log — lot 05)"
    pull_bq = bq["pull_date"] or "non relevé (aucun log — lot 05)"
    if bq["log"]:
        pull_bq += f" (log : {bq['log']})"
    pull_int = intent_pull or "non relevé (aucun brut — lot 06)"
    if n_raw_files:
        pull_int += f" ({n_raw_files} fichier(s) data/raw/)"
    bytes_cell = bq["bytes"]
    bytes_kind = bq.get("bytes_kind") or "scannés"
    try:
        bytes_cell_txt = f"{fmt_int(float(bytes_cell))} bytes {bytes_kind}" if bytes_cell else None
    except (TypeError, ValueError):
        bytes_cell_txt = f"{bytes_cell} bytes {bytes_kind}"
    fresh_rows = [
        ("MAX(block_date)", maxbd),
        ("Date de pull", f"BigQuery : {pull_bq} · Intents : {pull_int}"),
        ("Bytes BigQuery", bytes_cell_txt or "non relevés (aucun log — lot 05)"),
        ("Fenêtre", f"{dmin} → {dmax} ({n} jours ; plancher contractuel : 2026-10-01). "
                    "Note : Lake déprécié le 24/03/2026 — vérifier la fraîcheur via MAX(block_date)."),
    ]
    return maxbd, pull_bq, pull_int, fresh_rows


def _build_render_ctx(
    charts_dir: Path, queries_dir: Path, daily_path: Path, thesis_path: Path,
    out_path: Path, need_png: list, sql_text: dict[str, str],
    daily: dict[str, list], bq: dict[str, str | None], n_raw_files: int,
    intent_pull: str | None, verdict: dict[str, str], phrases: dict[str, str],
) -> dict:
    """Assemble le contexte de rendu (images, textes, liens, fraicheur)."""
    images = {
        png: base64.b64encode((charts_dir / png).read_bytes()).decode("ascii")
        for png, _, _ in need_png
    }
    details, qlinks = _build_details(queries_dir, out_path.parent, sql_text)
    maxbd, pull_bq, pull_int, fresh_rows = _fresh_pulls(
        bq, n_raw_files, intent_pull, daily)
    n = len(daily["date"])
    dmin, dmax = daily["date"][0], daily["date"][-1]
    return {
        "claim": CLAIM,
        "verdict": verdict,
        "dmin": dmin, "dmax": dmax, "n": n,
        "pull_bq": pull_bq, "pull_intents": pull_int, "maxbd": maxbd,
        "price": PRICE_NOTE,
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M"),
        "verdict_links": [
            ("rebuild.py", _rel(thesis_path.parent / "rebuild.py", out_path.parent)),
            ("THESIS.md", _rel(thesis_path, out_path.parent)),
            ("daily.csv", _rel(daily_path, out_path.parent)),
        ],
        "images": images,
        "details": details,
        "qlinks": qlinks,
        "phrases": phrases,
        "fresh_rows": fresh_rows,
    }


def build(
    charts_dir: Path,
    queries_dir: Path,
    daily_path: Path,
    raw_dir: Path,
    logs_dirs: list[Path],
    thesis_path: Path,
    top_contracts_path: Path | None,
    out_path: Path,
) -> Path:
    """Vérifie les entrées, génère dashboard.html, retourne son chemin."""
    need_png = _check_png_files(charts_dir)
    daily = _read_daily(daily_path)
    sql_text = _load_sql_texts(queries_dir)
    bq = _load_bq_meta(raw_dir, logs_dirs)
    raw_items, n_raw_files, intent_pull = _load_intents_raw(raw_dir)
    wallets, _skipped = _wallet_volumes(raw_items)
    top_contracts = _load_top_contracts(top_contracts_path)
    verdict = _load_verdict(thesis_path)
    phrases = _build_phrases(daily, bq, intent_pull, wallets, top_contracts)
    ctx = _build_render_ctx(
        charts_dir, queries_dir, daily_path, thesis_path, out_path,
        need_png, sql_text, daily, bq, n_raw_files, intent_pull,
        verdict, phrases,
    )
    page = build_html(ctx)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    root = _repo_root()
    p = argparse.ArgumentParser(description="Lot 12 : dashboard.html autonome (maquette §2-§5).")
    p.add_argument("--out", default=str(root / "dashboard.html"),
                   help="HTML de sortie (défaut : dashboard.html à la racine near-thesis/).")
    p.add_argument("--charts-dir", default=str(root / "charts"),
                   help="Dossier des PNG (défaut : charts/ sous near-thesis/).")
    p.add_argument("--queries-dir", default=str(root / "queries"),
                   help="Dossier des SQL (défaut : queries/ sous near-thesis/).")
    p.add_argument("--daily", default=str(root / "data" / "merged" / "daily.csv"),
                   help="CSV fusionné lot 07 (défaut : data/merged/daily.csv).")
    p.add_argument("--raw-dir", default=str(root / "data" / "raw"),
                   help="Brut Intents lot 06 (défaut : data/raw/).")
    p.add_argument("--logs-dir", default=None,
                   help="Dossier de logs BigQuery lot 05 (défaut : data/logs/ + logs/).")
    p.add_argument("--thesis", default=str(root / "THESIS.md"),
                   help="THESIS.md lot 13 (défaut : THESIS.md).")
    p.add_argument("--top-contracts", default=None,
                   help="CSV top-contrats explicite (défaut : data/merged/top_contracts.csv "
                        "sinon data/raw/bq_04_top_contracts.csv).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = _repo_root()
    logs_dirs = [Path(args.logs_dir)] if args.logs_dir else [root / "data" / "logs", root / "logs"]
    top_contracts = _resolve_top_contracts(args.top_contracts, root)
    try:
        written = build(
            Path(args.charts_dir), Path(args.queries_dir), Path(args.daily),
            Path(args.raw_dir), logs_dirs, Path(args.thesis),
            top_contracts, Path(args.out),
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        print(f"ERREUR : {exc}", file=sys.stderr)
        return 2
    print(f"OK : {written} ({len(BLOCKS)} blocs, PNG base64, CSS inline, 0 réseau)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
