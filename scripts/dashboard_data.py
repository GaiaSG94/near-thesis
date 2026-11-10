"""Lot 12 — Chargement des donnees reelles du dashboard (lot 12).

Extrait de ``build_dashboard.py`` : daily.csv requis (contrat lot 07),
logs BigQuery optionnels (lot 05), brut Intents optionnel (lot 06),
top contrats optionnel, verdict THESIS.md optionnel (lot 13).
Calculs et messages strictement identiques a l'original.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

try:
    from scripts.common import (
        aggregate_volumes_by_address,
        extract_payload_items,
        read_daily_columns,
    )
    from scripts.dashboard_content import VERDICT_BADGES, VERDICT_PENDING
except ImportError:  # execution directe : python scripts/xxx.py
    from common import (
        aggregate_volumes_by_address,
        extract_payload_items,
        read_daily_columns,
    )
    from dashboard_content import VERDICT_BADGES, VERDICT_PENDING

REQUIRED_DAILY_COLUMNS = (
    "date", "active_accounts", "tx_count", "contract_calls",
    "unique_contracts", "intents_swaps", "intents_volume_usd",
)

_BQ_PULL_KEYS = ("pull_date_utc", "pull_date", "pull_stamp", "pull_datetime",
                 "date", "date_pull")
_BQ_BYTES_KEYS = ("bytes_processed", "bytes_billed", "estimated_bytes_processed",
                  "bytes_scanned", "bytes")
_BQ_BYTES_KIND = {"bytes_processed": "scannés", "bytes_scanned": "scannés",
                  "bytes": "scannés", "bytes_billed": "facturés",
                  "estimated_bytes_processed": "estimés (dry-run)"}
_BQ_MAXBD_KEYS = ("max_block_date", "maxBlockDate", "MAX(block_date)", "max_date")


def _read_daily(path: Path) -> dict[str, list]:
    """Lit daily.csv (contrat lot 07), trié par date. Échec explicite sinon."""
    dates, values = read_daily_columns(
        path, REQUIRED_DAILY_COLUMNS,
        missing_suffix=" (contrat lot 07).", row_detail=False,
    )
    data: dict[str, list] = {"date": [d.isoformat() for d in dates]}
    for col in REQUIRED_DAILY_COLUMNS[1:]:
        data[col] = values[col]
    return data


def _pick(d: dict, keys: tuple[str, ...]) -> str | None:
    for k in keys:
        if d.get(k) not in (None, ""):
            return str(d[k])
    return None


def _meta_bytes(meta: dict) -> tuple[str | None, str | None]:
    for key in _BQ_BYTES_KEYS:
        if meta.get(key) not in (None, ""):
            return str(meta[key]), _BQ_BYTES_KIND[key]
    return None, None


def _aggregate_bq_metas(metas: list[dict], source: str) -> dict[str, str | None] | None:
    """Agrege le dernier pull d'un groupe de metas lot 05.

    pull_date = max des pull_date (lignes non dry_run sauf si seules des
    dry_run existent) ; bytes = somme sur les requetes de ce pull ;
    max_block_date = max observe. Lignes illisibles ignorees.
    """
    pool = [m for m in metas if not m.get("dry_run")] or metas
    dated = [(m, _pick(m, _BQ_PULL_KEYS) or "") for m in pool]
    if not dated:
        return None
    latest = max(p for _, p in dated)
    group = [m for m, p in dated if p == latest]
    total, counted, kinds = 0.0, 0, set()
    for m in group:
        val, kind = _meta_bytes(m)
        if val is None:
            continue
        try:
            total += float(val)
        except (TypeError, ValueError):
            continue
        counted += 1
        kinds.add(kind or "scannés")
    if all(m.get("dry_run") for m in group):
        kinds = {"estimés (dry-run)"}
    kind_txt = next(iter(kinds)) if len(kinds) == 1 else "scannés/facturés"
    maxbds = sorted(filter(None, (_pick(m, _BQ_MAXBD_KEYS) for m in group)))
    return {
        "pull_date": latest or None,
        "bytes": str(total) if counted else None,
        "bytes_kind": kind_txt,
        "max_block_date": maxbds[-1] if maxbds else None,
        "log": f"{source} ({len(group)} requête(s), pull {latest or 'sans date'})",
    }


def _read_jsonl_metas(jsonl_path: Path) -> list[dict]:
    """Metas du journal des pulls (lignes illisibles ignorees)."""
    metas: list[dict] = []
    if not jsonl_path.is_file():
        return metas
    try:
        text = jsonl_path.read_text(encoding="utf-8")
    except OSError:
        return metas
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            metas.append(obj)
    return metas


def _read_sidecar_metas(raw_dir: Path) -> list[dict]:
    """Metas des sidecars bq_*.meta.json (fichiers illisibles ignores)."""
    metas: list[dict] = []
    if not raw_dir.is_dir():
        return metas
    for f in sorted(raw_dir.glob("bq_*.meta.json")):
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(obj, dict):
            metas.append(obj)
    return metas


def _read_logs_metas(logs_dirs: list[Path]) -> list[dict]:
    """Metas mono-dict des dossiers de logs conventionnels."""
    metas: list[dict] = []
    for logs_dir in logs_dirs:
        if not logs_dir.is_dir():
            continue
        for f in sorted(logs_dir.glob("*.json")):
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(obj, dict):
                metas.append(obj)
    return metas


def _load_bq_meta(raw_dir: Path, logs_dirs: list[Path]) -> dict[str, str | None]:
    """Lit les logs BigQuery du lot 05 (priorite sans double-compte).

    1. data/raw/bq_pull_log.jsonl (JSON Lines, journal des pulls) ;
    2. sinon sidecars data/raw/bq_*.meta.json ;
    3. sinon *.json mono-dict des dossiers de logs conventionnels.
    Absents -> champs None (affichés « non relevé »), jamais inventés.
    """
    empty: dict[str, str | None] = {
        "pull_date": None, "bytes": None, "bytes_kind": "scannés",
        "max_block_date": None, "log": None,
    }
    metas = _read_jsonl_metas(raw_dir / "bq_pull_log.jsonl")
    agg = _aggregate_bq_metas(metas, "bq_pull_log.jsonl") if metas else None
    if agg:
        return agg
    metas = _read_sidecar_metas(raw_dir)
    agg = _aggregate_bq_metas(metas, "bq_*.meta.json") if metas else None
    if agg:
        return agg
    metas = _read_logs_metas(logs_dirs)
    agg = _aggregate_bq_metas(metas, "*.json (logs/)") if metas else None
    return agg or empty


def _payload_items(payload: object) -> list[dict]:
    """Liste des transactions d'un payload brut (voir scripts/common.py)."""
    return extract_payload_items(payload)


def _load_intents_raw(raw_dir: Path) -> tuple[list[dict], int, str | None]:
    """Retourne (transactions SUCCESS brutes, nb fichiers, pull_date max).

    Fichiers absents -> ([], 0, None) : les phrases concernées affichent
    « non calculable ». Fichier corrompu -> ValueError explicite.
    """
    items: list[dict] = []
    n_files = 0
    pull_dates: list[str] = []
    if not raw_dir.is_dir():
        return items, n_files, None
    for f in sorted(raw_dir.glob("intents_*.json")):
        try:
            envelope = json.loads(f.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Brut Intents corrompu : {f} ({exc}).") from exc
        n_files += 1
        if isinstance(envelope, dict):
            if envelope.get("pull_date"):
                pull_dates.append(str(envelope["pull_date"]))
            payload = envelope.get("payload", envelope)
        else:
            payload = envelope
        items.extend(_payload_items(payload))
    return items, n_files, (max(pull_dates) if pull_dates else None)


def _wallet_volumes(items: list[dict]) -> tuple[dict[str, float], int]:
    """Agrege le volume USD par adresse (SUCCESS, montant > 0).

    Retourne (volumes, nb ignores). Meme regle que le lot 11.
    """
    return aggregate_volumes_by_address(items)


def _resolve_top_contracts(explicit: str | None, root: Path) -> Path | None:
    """Resout le CSV top-contrats : --top-contracts, sinon
    data/merged/top_contracts.csv, sinon data/raw/bq_04_top_contracts.csv
    (artefact lot 05). None si aucun n'existe."""
    if explicit:
        return Path(explicit)
    for cand in (root / "data" / "merged" / "top_contracts.csv",
                 root / "data" / "raw" / "bq_04_top_contracts.csv"):
        if cand.is_file():
            return cand
    return None


def _load_top_contracts(path: Path | None) -> list[tuple[str, float]] | None:
    """Charge le CSV top-contrats (sortie de 04_top_contracts.sql).

    None -> None (phrase : « non calculable »). Chemin explicite absent ->
    FileNotFoundError (faute de frappe a corriger). Présent mais malformé ->
    ValueError explicite (bug de pipeline, echec propre).
    """
    if path is None:
        return None
    if not path.is_file():
        raise FileNotFoundError(f"CSV top-contrats introuvable : {path}.")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or "contract_id" not in reader.fieldnames \
                or "contract_calls" not in reader.fieldnames:
            raise ValueError(
                f"{path} malforme : colonnes contract_id + contract_calls "
                "requises (sortie de queries/04_top_contracts.sql)."
            )
        rows = []
        for i, row in enumerate(reader, start=2):
            try:
                rows.append((str(row["contract_id"]), float(row["contract_calls"])))
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Ligne {i} de {path} illisible : {exc}.") from exc
    rows.sort(key=lambda r: (-r[1], r[0]))
    return rows


def _load_verdict(thesis_path: Path) -> dict[str, str]:
    """Lit Verdict/Seuil/Phrase-verdict dans THESIS.md (lot 13).

    Absents -> mentions « non figé (lot 13) », jamais un verdict inventé.
    """
    out = {
        "badge_class": VERDICT_PENDING[0],
        "badge_label": VERDICT_PENDING[1],
        "seuil": "non figé (lot 13)",
        "phrase": "verdict à figer dans THESIS.md (lot 13)",
        "source": "THESIS.md absent",
    }
    if not thesis_path.is_file():
        return out
    found: dict[str, str] = {}
    for line in thesis_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*(verdict|seuil|phrase[\s_-]*verdict)\s*:\s*(.+?)\s*$",
                     line, re.IGNORECASE)
        if m:
            key = m.group(1).lower().replace("_", " ").replace("-", " ").replace(" ", "")
            found.setdefault("phraseverdict" if "phrase" in key else key,
                             m.group(2).strip().strip("`\"'"))
    raw = found.get("verdict", "").upper()
    if raw in VERDICT_BADGES:
        out["badge_class"], out["badge_label"] = VERDICT_BADGES[raw]
    elif raw:
        out["badge_class"], out["badge_label"] = "b-pending", raw[:24]
    if found.get("seuil"):
        out["seuil"] = found["seuil"]
    if found.get("phraseverdict"):
        out["phrase"] = found["phraseverdict"]
    out["source"] = thesis_path.name
    return out
