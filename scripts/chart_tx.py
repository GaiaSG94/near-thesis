"""Lot 09 — Charts transactions/jour et contrats uniques/jour.

Lit data/merged/daily.csv (contrat intent.md) et produit :
- charts/02_tx.png : transactions par jour (colonne tx_count) ;
- charts/03_contrats.png : contrats uniques par jour (colonne unique_contracts),
  avec annotation des top contrats si un CSV top-contrats est fourni.

Contrat CSV : date,active_accounts,tx_count,contract_calls,unique_contracts,
intents_swaps,intents_volume_usd.

CSV top-contrats optionnel (sortie de queries/04_top_contracts.sql) :
contract_id,contract_calls[,active_days].

Regle dure : aucune donnee fictive. Si le CSV daily est absent, vide ou
incomplet, les fonctions build_* echouent proprement avec une exception
explicite. Le CSV top-contrats est optionnel : absent => pas d'annotation,
jamais d'invention.
"""

from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

try:
    from scripts.common import finalize_figure as _finalize
    from scripts.common import new_figure as _new_figure
    from scripts.common import read_daily_columns
except ImportError:  # execution directe : python scripts/xxx.py
    from common import finalize_figure as _finalize
    from common import new_figure as _new_figure
    from common import read_daily_columns

REQUIRED_COLUMNS = ("date", "tx_count", "unique_contracts")

SOURCE_NOTE = (
    "Source : bigquery-public-data.crypto_near_mainnet_us "
    "(queries/02_tx_counts.sql, queries/03_contract_usage.sql)."
)

TOP_NOTE = "Top contrats : queries/04_top_contracts.sql."


def _read_daily(daily_csv: str | Path) -> tuple[list[date], list[float], list[float]]:
    """Lit daily.csv (colonnes lot 09), trie par date. Echec propre sinon."""
    dates, values = read_daily_columns(
        daily_csv, REQUIRED_COLUMNS,
        missing_suffix=f". Colonnes requises : {', '.join(REQUIRED_COLUMNS)}.",
    )
    return dates, values["tx_count"], values["unique_contracts"]


def _read_top_contracts(
    top_csv: str | Path, limit: int = 5
) -> list[tuple[str, int]]:
    """Lit le top contrats (contract_id, contract_calls). Echec propre si illisible."""
    path = Path(top_csv)
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError(f"CSV top-contrats vide ou sans en-tete : {path}.")
        for col in ("contract_id", "contract_calls"):
            if col not in reader.fieldnames:
                raise ValueError(
                    f"Colonne '{col}' manquante dans {path}. "
                    "Attendu : sortie de queries/04_top_contracts.sql "
                    "(contract_id,contract_calls[,active_days])."
                )
        entries: list[tuple[str, int]] = []
        for i, row in enumerate(reader, start=2):
            cid = (row.get("contract_id") or "").strip()
            if not cid:
                continue
            try:
                calls = int(float(row["contract_calls"]))
            except (ValueError, TypeError) as exc:
                raise ValueError(
                    f"Ligne {i} de {path} illisible "
                    f"(contract_id={cid!r}, "
                    f"contract_calls={row.get('contract_calls')!r}) : {exc}"
                ) from exc
            entries.append((cid, calls))
    if not entries:
        raise ValueError(f"CSV top-contrats sans donnees exploitables : {path}.")
    entries.sort(key=lambda e: (-e[1], e[0]))
    return entries[:limit]


def build_tx(daily_csv: str | Path, out_png: str | Path) -> Path:
    """Trace les transactions par jour et sauve le PNG.

    Args:
        daily_csv: chemin vers data/merged/daily.csv.
        out_png: chemin de sortie, attendu charts/02_tx.png.

    Returns:
        Le chemin du PNG ecrit.

    Raises:
        FileNotFoundError: si le CSV source est absent.
        ValueError: si le CSV est vide, incomplet ou illisible.
    """
    dates, tx_counts, _ = _read_daily(daily_csv)

    fig, ax, _ = _new_figure()
    ax.plot(dates, tx_counts, color="#2ca02c", linewidth=2)
    ax.set_xlabel("Date")
    ax.set_ylabel("Transactions / jour")
    ax.set_title("NEAR — Transactions par jour")
    ax.grid(True, alpha=0.3)
    fig.text(0.01, 0.01, SOURCE_NOTE, fontsize=7, color="gray", ha="left", va="bottom")
    return _finalize(fig, out_png)


def _annotate_top_contracts(ax, top_contracts_csv: str | Path | None, top_n: int) -> str:
    """Annote les top contrats si le CSV existe. Retourne la note source."""
    note = SOURCE_NOTE
    if top_contracts_csv is not None:
        top_path = Path(top_contracts_csv)
        if top_path.is_file():
            top = _read_top_contracts(top_path, limit=top_n)
            lines = [f"Top {len(top)} contrats (appels) :"]
            lines += [f"{cid} — {calls:,}" for cid, calls in top]
            ax.text(
                0.02,
                0.97,
                "\n".join(lines),
                transform=ax.transAxes,
                fontsize=8,
                va="top",
                ha="left",
                family="monospace",
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
            )
            note = SOURCE_NOTE + " " + TOP_NOTE
        # Fichier top-contrats absent => pas d'annotation, pas d'echec.
    return note


def build_contrats(
    daily_csv: str | Path,
    out_png: str | Path,
    top_contracts_csv: str | Path | None = None,
    top_n: int = 5,
) -> Path:
    """Trace les contrats uniques par jour, annote des top contrats si dispo.

    Args:
        daily_csv: chemin vers data/merged/daily.csv.
        out_png: chemin de sortie, attendu charts/03_contrats.png.
        top_contracts_csv: CSV optionnel issu de queries/04_top_contracts.sql.
            Absent ou None => aucune annotation. Present mais illisible =>
            ValueError explicite.
        top_n: nombre de top contrats affiches dans l'annotation.

    Returns:
        Le chemin du PNG ecrit.

    Raises:
        FileNotFoundError: si le CSV daily source est absent.
        ValueError: si le CSV daily est vide, incomplet ou illisible,
            ou si le CSV top-contrats fourni est illisible.
    """
    dates, _, unique_contracts = _read_daily(daily_csv)

    fig, ax, _ = _new_figure()
    ax.plot(dates, unique_contracts, color="#9467bd", linewidth=2)
    ax.set_xlabel("Date")
    ax.set_ylabel("Contrats uniques / jour")
    ax.set_title("NEAR — Contrats uniques par jour (FUNCTION_CALL)")
    ax.grid(True, alpha=0.3)

    note = _annotate_top_contracts(ax, top_contracts_csv, top_n)
    fig.text(0.01, 0.01, note, fontsize=7, color="gray", ha="left", va="bottom")
    return _finalize(fig, out_png)


def build(
    daily_csv: str | Path,
    tx_png: str | Path = "charts/02_tx.png",
    contrats_png: str | Path = "charts/03_contrats.png",
    top_contracts_csv: str | Path | None = None,
) -> tuple[Path, Path]:
    """Construit les deux charts du lot 09 (pratique pour rebuild.py).

    Returns:
        Les chemins (tx_png, contrats_png) ecrits.
    """
    return (
        build_tx(daily_csv, tx_png),
        build_contrats(daily_csv, contrats_png, top_contracts_csv),
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Lot 09 : charts transactions/jour + contrats uniques/jour."
    )
    parser.add_argument(
        "--daily",
        default="data/merged/daily.csv",
        help="Chemin du CSV fusionne (defaut : data/merged/daily.csv).",
    )
    parser.add_argument(
        "--tx-out",
        default="charts/02_tx.png",
        help="PNG transactions (defaut : charts/02_tx.png).",
    )
    parser.add_argument(
        "--contrats-out",
        default="charts/03_contrats.png",
        help="PNG contrats uniques (defaut : charts/03_contrats.png).",
    )
    parser.add_argument(
        "--top-contracts",
        default=None,
        help="CSV top-contrats optionnel (queries/04_top_contracts.sql).",
    )
    args = parser.parse_args()
    tx_path, contrats_path = build(
        args.daily, args.tx_out, args.contrats_out, args.top_contracts
    )
    print(f"OK : {tx_path} + {contrats_path}")
