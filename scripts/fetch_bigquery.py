#!/usr/bin/env python3
"""Lot 05 — Pull BigQuery pour near-thesis.

Execute chaque fichier ``queries/*.sql`` sur
``bigquery-public-data.crypto_near_mainnet_us`` et sauvegarde le brut sous
``data/raw/bq_*.csv`` avec un sidecar ``.meta.json`` par requete.

Chaque pull loggue (contrat intent.md) :
  - date de pull (UTC),
  - bytes scannes / factures par BigQuery,
  - MAX(block_date) observe dans le resultat (fraicheur, cf. Lake deprecie
    le 24/03/2026 — la fraicheur est notee dans THESIS.md, jamais inventee).

Fenêtre d'analyse : lue depuis la constante START_DATE ci-dessous
(contrat : ``block_date >= '2026-10-01'``). Les fichiers SQL peuvent
referencer la fenetre via le placeholder textuel ``{START_DATE}`` ou le
parametre de requete ``@start_date`` ; sinon la requete est executee telle
quelle (les lots 02-04 codent le filtre en dur dans ce cas).

Dependances : stdlib + ``google-cloud-bigquery`` uniquement.
Sans credentials, le script echoue proprement (exit 2) avec un message
clair au lieu de produire des CSV vides.

Usage (depuis near-thesis/) :
    python scripts/fetch_bigquery.py
    python scripts/fetch_bigquery.py --dry-run        # estime les bytes, sans rien ecrire
    python scripts/fetch_bigquery.py --start-date 2026-10-01
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------- Constantes
# Fenetre d'analyse (contrat data intent.md). Surchargeable via --start-date.
START_DATE = "2026-10-01"

# Dataset impose (lots 01-04). Rappele ici a titre documentaire ; les SQL
# portent les noms de tables exacts tranches par le lot 01.
BQ_DATASET = "bigquery-public-data.crypto_near_mainnet_us"
BQ_LOCATION = "US"  # les datasets publics *crypto_* sont en multi-region US

ROOT = Path(__file__).resolve().parents[1]
QUERIES_DIR = ROOT / "queries"
RAW_DIR = ROOT / "data" / "raw"

# Noms de colonnes candidats pour la fraicheur MAX(block_date), par priorite.
DATE_COLUMNS = ("block_date", "date", "day")

AUTH_HELP = (
    "BigQuery : credentials introuvables.\n"
    "  1. `pip install -r requirements.txt` (fournit google-cloud-bigquery),\n"
    "  2. `gcloud auth application-default login`,\n"
    "  3. relancer `python scripts/fetch_bigquery.py` (ou `python rebuild.py`).\n"
    "Sans credentials, aucun CSV n'est ecrit : rebuild.py bascule sur le brut\n"
    "existant dans data/raw/."
)


# ------------------------------------------------------------------- Utils
def utcnow_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _cell(value):
    """Convertit une cellule BigQuery en valeur CSV plate (stdlib only)."""
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (dt.date, dt.datetime)):
        return value.isoformat()
    return str(value)


def prepare_sql(text: str, start_date: str):
    """Injecte la fenetre. Retourne (sql, query_params).

    - ``{START_DATE}`` (placeholder textuel) est substitue, sans toucher au
      reste du SQL ;
    - si le SQL reference ``@start_date``, un parametre nomme est passe ;
    - sinon la requete est inchangee et sans parametre.
    """
    params = []
    if "{START_DATE}" in text:
        text = text.replace("{START_DATE}", start_date)
    if "@start_date" in text:
        from google.cloud import bigquery

        params = [
            bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        ]
    return text, params


def check_block_date_filter(text: str, name: str) -> None:
    """Garde-fou jury : chaque SQL doit filtrer sur block_date."""
    if "block_date" not in text:
        print(
            f"AVERTISSEMENT: {name} ne mentionne pas block_date "
            "(filtre partition obligatoire, cf. intent.md).",
            file=sys.stderr,
        )


def max_date_of(rows: list[dict], fieldnames: list[str]) -> str | None:
    """MAX(block_date) observe dans le resultat, ou None si non calculable.

    Ne note que ce qui est observe : aucune valeur par defaut inventee.
    """
    col = next((c for c in DATE_COLUMNS if c in fieldnames), None)
    if col is None:
        return None
    values = sorted(v for v in (r.get(col) for r in rows) if v not in (None, ""))
    if not values:
        return None
    last = values[-1]
    if isinstance(last, (dt.date, dt.datetime)):
        return last.isoformat()
    return str(last)


# ------------------------------------------------------------------- Coeur
def build_client():
    """Cree le client BigQuery ou leve RuntimeError avec message clair."""
    try:
        from google.cloud import bigquery
    except ImportError as exc:  # dependance absente
        raise RuntimeError(
            "Module google-cloud-bigquery absent.\n" + AUTH_HELP
        ) from exc
    try:
        from google.auth import default as google_auth_default
        from google.auth.exceptions import DefaultCredentialsError

        credentials, project = google_auth_default()
    except Exception as exc:  # DefaultCredentialsError et derives
        raise RuntimeError(AUTH_HELP) from exc
    try:
        return bigquery.Client(
            project=project, credentials=credentials, location=BQ_LOCATION
        )
    except Exception as exc:
        raise RuntimeError(AUTH_HELP) from exc


def _read_sql_file(sql_path: Path) -> str:
    """Lit un fichier SQL, refuse les fichiers vides."""
    text = sql_path.read_text(encoding="utf-8")
    if not text.strip():
        raise RuntimeError(f"{sql_path.name} est vide : rien a executer.")
    return text


def _estimate_bytes(client, sql: str, params: list) -> int:
    """Estimation dry-run des bytes (sans rien executer ni ecrire)."""
    from google.cloud import bigquery

    job_config = bigquery.QueryJobConfig(
        query_parameters=params, dry_run=True, use_query_cache=False
    )
    estimated = client.query(sql, job_config=job_config)
    return estimated.total_bytes_processed


def _new_bq_meta(query_name: str, start_date: str, pull_date: str,
                 estimated_bytes: int, dry_run: bool) -> dict:
    """Metadonnees initiales d'un pull (completees apres execution)."""
    return {
        "query_file": query_name,
        "start_date": start_date,
        "pull_date_utc": pull_date,
        "estimated_bytes_processed": estimated_bytes,
        "dry_run": dry_run,
        "csv": None,
        "row_count": 0,
        "bytes_processed": None,
        "bytes_billed": None,
        "max_block_date": None,
        "job_id": None,
    }


def _write_bq_csv(csv_path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    """Ecrit le brut CSV (cellules aplaties en valeurs plates)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _cell(v) for k, v in row.items()})


def run_query_file(client, sql_path: Path, start_date: str, dry_run: bool = False) -> dict:
    """Execute un fichier SQL, ecrit CSV + sidecar JSON. Retourne les metadonnees."""
    from google.cloud import bigquery

    name = sql_path.stem  # ex. 01_active_accounts
    text = _read_sql_file(sql_path)
    check_block_date_filter(text, sql_path.name)
    sql, params = prepare_sql(text, start_date)

    pull_date = utcnow_iso()
    estimated_bytes = _estimate_bytes(client, sql, params)
    meta = _new_bq_meta(sql_path.name, start_date, pull_date,
                        estimated_bytes, dry_run)

    if dry_run:
        print(f"[dry-run] {sql_path.name} : ~{estimated_bytes} bytes scannes.")
        return meta

    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(query_parameters=params),
        location=BQ_LOCATION,
    )
    rows_iter = job.result()  # attend la fin du job (leve sur erreur SQL)
    fieldnames = [f.name for f in rows_iter.schema]
    rows = [dict(zip(fieldnames, row)) for row in rows_iter]

    csv_path = RAW_DIR / f"bq_{name}.csv"
    _write_bq_csv(csv_path, fieldnames, rows)

    meta.update(
        {
            "csv": csv_path.name,
            "row_count": len(rows),
            "bytes_processed": job.total_bytes_processed,
            "bytes_billed": job.total_bytes_billed,
            "max_block_date": max_date_of(rows, fieldnames),
            "job_id": job.job_id,
        }
    )
    meta_path = RAW_DIR / f"bq_{name}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return meta


def append_cost_log(metas: list[dict]) -> Path:
    """Journalise chaque pull (couts + fraicheur) en JSON Lines."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RAW_DIR / "bq_pull_log.jsonl"
    with log_path.open("a", encoding="utf-8") as fh:
        for meta in metas:
            fh.write(json.dumps(meta, ensure_ascii=False) + "\n")
    return log_path


def run_pull(start_date: str = START_DATE, dry_run: bool = False) -> list[dict]:
    """Point d'entree appelable depuis rebuild.py. Retourne les metadonnees."""
    if not QUERIES_DIR.is_dir():
        raise RuntimeError(f"Dossier SQL introuvable : {QUERIES_DIR}")
    sql_files = sorted(QUERIES_DIR.glob("*.sql"))
    if not sql_files:
        raise RuntimeError(f"Aucun *.sql dans {QUERIES_DIR} (lots 01-04 requis).")

    client = build_client()
    metas = []
    for sql_path in sql_files:
        meta = run_query_file(client, sql_path, start_date, dry_run=dry_run)
        metas.append(meta)
        print(
            f"[bigquery] {meta['query_file']} -> {meta['csv'] or '(dry-run)'} "
            f"({meta['row_count']} lignes, "
            f"bytes_billed={meta['bytes_billed']}, "
            f"MAX(block_date)={meta['max_block_date']})"
        )
    if not dry_run:
        log_path = append_cost_log(metas)
        print(f"[bigquery] journal des pulls : {log_path.name}")
    return metas


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute queries/*.sql sur BigQuery et sauve le brut + metadonnees."
    )
    parser.add_argument(
        "--start-date",
        default=START_DATE,
        help=f"Debut de fenetre block_date (defaut : {START_DATE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Estime les bytes scannes sans executer ni ecrire.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        run_pull(start_date=args.start_date, dry_run=args.dry_run)
    except RuntimeError as exc:
        print(f"ERREUR: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrompu.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
