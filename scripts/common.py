"""Module partage near-thesis (agents.md regle 3 : zero duplication).

Regroupe la logique utilisee par plusieurs scripts, sans effet de bord a
l'import (stdlib uniquement) :
- lecture validee de ``data/merged/daily.csv`` (lots 07-10, 12) ;
- creation/sauvegarde des figures matplotlib (lots 08-09) ;
- extraction des transactions depuis le brut Intents (lots 06, 11, 12).

Import robuste en execution directe (``python scripts/xxx.py``, cwd =
near-thesis/) comme en import paquet : chaque script fait::

    try:
        from scripts.common import ...
    except ImportError:
        from common import ...

Aucune dependance hors requirements.txt (ce module : stdlib uniquement).
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

MERGE_HINT = (
    "Lancez d'abord le lot 07 (merge) "
    "pour produire data/merged/daily.csv. Aucune donnee fictive generee."
)

# Champs volume essayes dans l'ordre (entree puis sortie, cf. intent.md).
INTENTS_VOLUME_KEYS = (
    "amountInUsd",
    "amount_in_usd",
    "inUsd",
    "amountOutUsd",
    "amount_out_usd",
    "outUsd",
)

# Champs adresse essayes dans l'ordre (adresse de depot d'abord).
INTENTS_ADDRESS_KEYS = (
    "depositAddress",
    "lastDepositAddress",
    "fromAddress",
    "sender",
    "signer",
    "address",
)

INTENTS_ADDRESS_PARENTS = ("deposit", "from", "sender")

# Cles de liste reconnues dans un payload brut ou une reponse API.
INTENTS_LIST_KEYS = ("transactions", "data", "items", "results")


def load_csv_rows(
    daily_csv: str | Path,
    required_columns: tuple[str, ...],
    missing_suffix: str = "",
) -> tuple[Path, list[dict]]:
    """Ouvre un CSV journalier, controle l'en-tete, retourne les lignes.

    Echec propre (FileNotFoundError / ValueError explicites), sans donnee
    fictive. ``missing_suffix`` est ajoute tel quel au message de colonnes
    manquantes (chaque lot garde son libelle historique).
    """
    path = Path(daily_csv)
    if not path.is_file():
        raise FileNotFoundError(f"CSV introuvable : {path}. {MERGE_HINT}")
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"CSV vide ou sans en-tete : {path}.")
        missing = [c for c in required_columns if c not in reader.fieldnames]
        if missing:
            raise ValueError(
                f"Colonnes manquantes dans {path} : {', '.join(missing)}"
                f"{missing_suffix}"
            )
        rows = [r for r in reader if r and (r.get("date") or "").strip()]
    if not rows:
        raise ValueError(f"CSV sans donnees exploitables : {path}.")
    return path, rows


def _row_error(
    path: Path,
    lineno: int,
    row: dict,
    value_columns: list[str],
    exc: Exception,
    row_detail: bool,
) -> ValueError:
    """Construit l'erreur de ligne illisible (formats historiques)."""
    if not row_detail:
        return ValueError(f"Ligne {lineno} de {path} illisible : {exc}")
    cols = ", ".join(f"{c}={row.get(c)!r}" for c in ["date", *value_columns])
    return ValueError(f"Ligne {lineno} de {path} illisible ({cols}) : {exc}")


def read_daily_columns(
    daily_csv: str | Path,
    required_columns: tuple[str, ...],
    *,
    missing_suffix: str = "",
    row_detail: bool = True,
) -> tuple[list[date], dict[str, list[float]]]:
    """Lit un CSV journalier -> (dates triees, {colonne: valeurs}).

    Factorise ``_read_daily`` des lots 08/09 et 12 : memes controles, memes
    messages, tri par date croissante. ``row_detail=False`` donne le format
    d'erreur court du lot 12.
    """
    path, rows = load_csv_rows(daily_csv, required_columns, missing_suffix)
    value_columns = [c for c in required_columns if c != "date"]
    dates: list[date] = []
    values: dict[str, list[float]] = {c: [] for c in value_columns}
    for i, row in enumerate(rows, start=2):  # ligne 1 = en-tete
        try:
            parsed = date.fromisoformat(row["date"].strip())
            parsed_vals = [float(row[col]) for col in value_columns]
        except (ValueError, TypeError) as exc:
            raise _row_error(path, i, row, value_columns, exc, row_detail) from exc
        dates.append(parsed)
        for col, val in zip(value_columns, parsed_vals):
            values[col].append(val)
    order = sorted(range(len(dates)), key=lambda k: dates[k])
    return [dates[k] for k in order], {
        c: [vals[k] for k in order] for c, vals in values.items()
    }


def new_figure(figsize: tuple[float, float] = (10, 5.5)):
    """Cree une figure matplotlib (backend Agg : sans ecran)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax, plt


def finalize_figure(fig, out_png: str | Path, *, dpi: int = 150) -> Path:
    """Mise en page + sauvegarde PNG + fermeture (lots 08-09)."""
    import matplotlib.pyplot as plt

    fig.autofmt_xdate()
    fig.tight_layout()
    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=dpi)
    plt.close(fig)
    return out


def extract_payload_items(payload: object) -> list[dict]:
    """Liste des transactions d'un payload brut ou d'une reponse API."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in INTENTS_LIST_KEYS:
            val = payload.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
    return []


def extract_envelope_items(envelope: dict | list) -> list[dict]:
    """Liste des transactions d'un fichier brut (enveloppe ou liste)."""
    payload = envelope.get("payload", envelope) if isinstance(envelope, dict) else envelope
    return extract_payload_items(payload)


def tx_status_ok(tx: dict) -> bool:
    """Ne garde que les SUCCESS (brut deja filtre, controle defensif)."""
    for key in ("status", "transactionStatus"):
        val = tx.get(key)
        if val is not None:
            return str(val).upper() == "SUCCESS"
    return True


def tx_volume_usd(tx: dict) -> float | None:
    """Montant USD strictement positif d'une transaction, ou None."""
    for key in INTENTS_VOLUME_KEYS:
        val = tx.get(key)
        if val is None:
            continue
        try:
            amount = float(val)
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return None


def tx_address(tx: dict) -> str | None:
    """Adresse de depot (ou expediteur) d'une transaction, ou None."""
    for key in INTENTS_ADDRESS_KEYS:
        val = tx.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    for parent in INTENTS_ADDRESS_PARENTS:
        node = tx.get(parent)
        if isinstance(node, dict):
            addr = node.get("address")
            if isinstance(addr, str) and addr.strip():
                return addr.strip()
    return None


def aggregate_volumes_by_address(items: list[dict]) -> tuple[dict[str, float], int]:
    """Agrege le volume USD par adresse (SUCCESS, montant > 0).

    Retourne (volumes, nb ignores). Meme regle que le lot 11.
    """
    volumes: dict[str, float] = {}
    skipped = 0
    for tx in items:
        if not tx_status_ok(tx):
            skipped += 1
            continue
        addr, usd = tx_address(tx), tx_volume_usd(tx)
        if addr is None or usd is None:
            skipped += 1
            continue
        volumes[addr] = volumes.get(addr, 0.0) + usd
    return volumes, skipped
