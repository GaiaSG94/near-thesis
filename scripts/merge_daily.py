#!/usr/bin/env python3
"""Lot 07 — Fusion du brut BigQuery + Intents en ``data/merged/daily.csv``.

Entrees (dossier ``data/raw/``) :
  - ``bq_01_active_accounts.csv`` : ``date,active_accounts`` (lot 02/05)
  - ``bq_02_tx_counts.csv``        : ``date,tx_count`` (lot 03/05)
  - ``bq_03_contract_usage.csv``   : ``date,contract_calls,unique_contracts`` (lot 04/05)
  - ``intents_*.json``             : pulls bruts du lot 06 (enveloppes avec
    champ ``payload``) ou listes brutes de transactions.

Sortie (contrat data fixe, intent.md) :
  ``data/merged/daily.csv`` :
  ``date,active_accounts,tx_count,contract_calls,unique_contracts,intents_swaps,intents_volume_usd``

Regles :
  - ``intents_swaps`` = nombre de transactions Intents SUCCESS par jour.
  - ``intents_volume_usd`` = somme ``amountInUsd`` des SUCCESS par jour
    (repli ``amountOutUsd`` si ``amountInUsd`` absent ; jour UTC tire de
    ``createdAtTimestamp``).
  - Idempotent : memes entrees => memes octets (tri par date, dedup des
    transactions Intents vues dans plusieurs pulls, ecriture atomique).
  - Stdlib uniquement. Aucune donnee inventee : une source absente donne
    des zeros explicites (loggues) ; sans aucune donnee exploitable, le
    script echoue (exit 1) sans rien ecrire.

Usage (depuis near-thesis/) :
    python scripts/merge_daily.py
    python scripts/merge_daily.py --raw-dir data/raw --out data/merged/daily.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RAW_DIR = ROOT / "data" / "raw"
DEFAULT_OUT = ROOT / "data" / "merged" / "daily.csv"

OUTPUT_COLUMNS = (
    "date", "active_accounts", "tx_count", "contract_calls",
    "unique_contracts", "intents_swaps", "intents_volume_usd",
)

# Fichiers BigQuery agreges par jour reconnus. Les autres ``bq_*.csv`` sont
# ignores : 00_sample = lignes par transaction, 04_top_contracts = lignes
# par contrat (ni l'un ni l'autre n'est un agregat journalier).
BQ_SOURCES = {
    "bq_01_active_accounts.csv": ("active_accounts",),
    "bq_02_tx_counts.csv": ("tx_count",),
    "bq_03_contract_usage.csv": ("contract_calls", "unique_contracts"),
}

DATE_COLUMNS = ("date", "block_date", "day")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")
INT_COLUMNS = (
    "active_accounts", "tx_count", "contract_calls",
    "unique_contracts", "intents_swaps",
)


def _log(msg: str) -> None:
    print(msg, flush=True)


def _parse_date(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if not DATE_RE.match(s):
        return None
    try:
        dt.date.fromisoformat(s)
    except ValueError:
        return None
    return s


def _parse_number(value: object) -> float | None:
    if value is None:
        return None
    s = str(value).strip().replace(" ", "").replace(",", "")
    if not s or not NUM_RE.match(s):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def read_bq_daily(path: Path, columns: tuple[str, ...]) -> dict[str, dict[str, int]]:
    """Lit un CSV BigQuery journalier -> {date: {colonne: valeur}}."""
    out: dict[str, dict[str, int]] = {}
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"{path.name} : CSV vide ou sans en-tete.")
        date_col = next((c for c in DATE_COLUMNS if c in reader.fieldnames), None)
        if date_col is None:
            raise ValueError(
                f"{path.name} : colonne date introuvable "
                f"(cherche {DATE_COLUMNS}, trouve {reader.fieldnames})."
            )
        missing = [c for c in columns if c not in reader.fieldnames]
        if missing:
            raise ValueError(f"{path.name} : colonnes manquantes {missing}.")
        for lineno, row in enumerate(reader, start=2):
            day = _parse_date(row.get(date_col))
            if day is None:
                _log(f"[warn] {path.name} ligne {lineno} : date illisible "
                      f"({row.get(date_col)!r}), ligne ignoree.")
                continue
            vals: dict[str, int] = {}
            for col in columns:
                num = _parse_number(row.get(col))
                if num is None:
                    _log(f"[warn] {path.name} ligne {lineno} : {col} illisible "
                          f"({row.get(col)!r}), mis a 0.")
                    num = 0
                vals[col] = int(num)
            if day in out:
                _log(f"[warn] {path.name} : date {day} en double, "
                      "derniere valeur gardee.")
            out[day] = vals
    return out


def _iter_intent_items(doc: object) -> list[dict]:
    """Extrait les transactions d'un brut Intents (enveloppe ou liste)."""
    payload = doc
    if isinstance(doc, dict) and "payload" in doc:
        payload = doc["payload"]
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("transactions", "data", "items", "results"):
            val = payload.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        if "createdAtTimestamp" in payload or "amountInUsd" in payload:
            return [payload]  # objet transaction unique
    return []


def _is_success(item: dict) -> bool:
    """Filtre SUCCESS. Sans champ statut, on garde (pulls deja filtres
    ``statuses=SUCCESS`` cote serveur par le lot 06)."""
    for key in ("status", "state"):
        if key in item and item[key] is not None:
            return str(item[key]).strip().lower() == "success"
    return True


def _parse_amount(item: dict) -> tuple[float, bool]:
    for key in ("amountInUsd", "amountOutUsd"):
        num = _parse_number(item.get(key))
        if num is not None:
            return num, True
    return 0.0, False


def _epoch_to_day(value: float) -> str | None:
    if value >= 1e14:  # microsecondes
        value /= 1e6
    elif value >= 1e11:  # millisecondes
        value /= 1e3
    try:
        return dt.datetime.fromtimestamp(value, tz=dt.timezone.utc).date().isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _tx_day(item: dict) -> str | None:
    raw = item.get("createdAtTimestamp", item.get("createdAt"))
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return _epoch_to_day(float(raw))
    s = str(raw).strip()
    if NUM_RE.match(s):
        return _epoch_to_day(float(s))
    try:  # ISO 8601 (tolere le suffixe Z)
        parsed = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc).date().isoformat()


def _tx_key(item: dict) -> tuple:
    deposit = item.get("deposit")
    deposit_addr = deposit.get("address") if isinstance(deposit, dict) else None
    deposit_memo = deposit.get("memo") if isinstance(deposit, dict) else None
    addr = item.get("depositAddress") or deposit_addr
    memo = item.get("depositMemo", item.get("lastDepositMemo", deposit_memo))
    if addr is not None and memo is not None:
        return ("addr+memo", str(addr), str(memo))
    for key in ("transactionHash", "hash", "id", "intentHash", "orderId"):
        if item.get(key) is not None and str(item[key]) != "":
            return (key, str(item[key]))
    return ("_body", json.dumps(item, sort_keys=True, default=str))


def read_intents_daily(paths: list[Path]) -> tuple[dict[str, dict[str, float]], dict[str, int]]:
    """Agrege les bruts Intents -> ({jour: {swaps, volume}}, stats)."""
    per_day: dict[str, dict[str, float]] = {}
    stats = {"files": 0, "items": 0, "success": 0, "dups": 0,
             "no_date": 0, "no_amount": 0}
    seen: set[tuple] = set()
    for path in paths:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            _log(f"[warn] {path.name} : JSON illisible ({exc}), fichier ignore.")
            continue
        stats["files"] += 1
        for item in _iter_intent_items(doc):
            stats["items"] += 1
            if not _is_success(item):
                continue
            key = _tx_key(item)
            if key in seen:
                stats["dups"] += 1
                continue
            seen.add(key)
            day = _tx_day(item)
            if day is None:
                stats["no_date"] += 1
                continue
            amount, has_amount = _parse_amount(item)
            if not has_amount:
                stats["no_amount"] += 1
            slot = per_day.setdefault(day, {"swaps": 0, "volume": 0.0})
            slot["swaps"] += 1
            slot["volume"] += amount
            stats["success"] += 1
    return per_day, stats


def _collect_bq_days(raw_dir: Path, days: dict[str, dict[str, float]],
                     sources_ok: list[str], sources_missing: list[str]) -> None:
    """Agrege les CSV BigQuery journaliers (zeros si source absente)."""
    for fname, columns in BQ_SOURCES.items():
        path = raw_dir / fname
        if not path.is_file():
            sources_missing.append(fname)
            continue
        for day, vals in read_bq_daily(path, columns).items():
            days.setdefault(day, {}).update(vals)
        # Double lecture d'origine preservee (donnees + compteur du message).
        sources_ok.append(f"{fname} ({len(read_bq_daily(path, columns))} jours)")


def _collect_intents_days(raw_dir: Path, days: dict[str, dict[str, float]],
                          sources_ok: list[str], sources_missing: list[str]) -> None:
    """Agrege les bruts Intents dedupes (swaps + volume par jour UTC)."""
    intent_files = sorted(raw_dir.glob("intents_*.json"))
    if not intent_files:
        sources_missing.append("intents_*.json (aucun fichier)")
        return
    per_day, stats = read_intents_daily(intent_files)
    for day, vals in per_day.items():
        slot = days.setdefault(day, {})
        slot["intents_swaps"] = vals["swaps"]
        slot["intents_volume_usd"] = vals["volume"]
    sources_ok.append(
        f"{stats['files']} fichier(s) intents_*.json "
        f"({stats['success']} SUCCESS uniques, {stats['dups']} doublons "
        f"dedupes, {stats['no_date']} sans date ignorees, "
        f"{stats['no_amount']} sans montant comptees a 0)")


def _write_daily_csv(out_path: Path, days: dict[str, dict[str, float]]) -> None:
    """Ecrit daily.csv (tri par date, ecriture atomique, zeros par defaut)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(
        prefix="daily_", suffix=".csv", dir=str(out_path.parent))
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(OUTPUT_COLUMNS))
            writer.writeheader()
            for day in sorted(days):
                vals = days[day]
                row: dict[str, str] = {"date": day}
                row["active_accounts"] = str(int(vals.get("active_accounts", 0)))
                row["tx_count"] = str(int(vals.get("tx_count", 0)))
                row["contract_calls"] = str(int(vals.get("contract_calls", 0)))
                row["unique_contracts"] = str(int(vals.get("unique_contracts", 0)))
                row["intents_swaps"] = str(int(vals.get("intents_swaps", 0)))
                row["intents_volume_usd"] = f"{round(float(vals.get('intents_volume_usd', 0.0)), 2):.2f}"
                writer.writerow(row)
        os.replace(tmp_name, out_path)  # ecriture atomique
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def merge(raw_dir: Path, out_path: Path,
          start: str | None = None, end: str | None = None) -> dict:
    """Fusionne ``raw_dir`` vers ``out_path``. Retourne un resume."""
    days: dict[str, dict[str, float]] = {}
    sources_ok: list[str] = []
    sources_missing: list[str] = []

    _collect_bq_days(raw_dir, days, sources_ok, sources_missing)
    _collect_intents_days(raw_dir, days, sources_ok, sources_missing)

    if start is not None:
        days = {d: v for d, v in days.items() if d >= start}
    if end is not None:
        days = {d: v for d, v in days.items() if d <= end}
    if not days:
        raise RuntimeError(
            f"Aucune donnee exploitable dans {raw_dir} "
            "(sources attendues : " + ", ".join(list(BQ_SOURCES) + ["intents_*.json"]) + "). "
            "Rien n'a ete ecrit."
        )

    _write_daily_csv(out_path, days)

    ordered = sorted(days)
    return {"sources_ok": sources_ok, "sources_missing": sources_missing,
            "rows": len(ordered), "first": ordered[0], "last": ordered[-1]}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fusionne data/raw en data/merged/daily.csv.")
    p.add_argument("--raw-dir", default=str(DEFAULT_RAW_DIR),
                   help="Dossier brut (defaut : data/raw sous near-thesis/).")
    p.add_argument("--out", default=str(DEFAULT_OUT),
                   help="CSV de sortie (defaut : data/merged/daily.csv).")
    p.add_argument("--start", default=None,
                   help="Jour min inclus (YYYY-MM-DD, optionnel).")
    p.add_argument("--end", default=None,
                   help="Jour max inclus (YYYY-MM-DD, optionnel).")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    for label, val in (("--start", args.start), ("--end", args.end)):
        if val is not None and _parse_date(val) is None:
            print(f"ERREUR : {label}={val!r} n'est pas un jour YYYY-MM-DD.",
                  file=sys.stderr)
            return 2
    try:
        summary = merge(Path(args.raw_dir), Path(args.out),
                        start=args.start, end=args.end)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"ERREUR merge : {exc}", file=sys.stderr)
        return 1
    _log(f"[merge] sources OK : {len(summary['sources_ok'])}")
    for s in summary["sources_ok"]:
        _log(f"  + {s}")
    for s in summary["sources_missing"]:
        _log(f"  ! manquant (zeros) : {s}")
    _log(f"[merge] {args.out} : {summary['rows']} jours, "
          f"{summary['first']} -> {summary['last']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
