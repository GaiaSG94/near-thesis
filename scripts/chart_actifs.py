"""Lot 08 — Chart actifs quotidiens vs volume Intents (double axe).

Lit data/merged/daily.csv (contrat intent.md) et produit charts/01_actifs_intents.png.

Contrat CSV : date,active_accounts,tx_count,contract_calls,unique_contracts,
intents_swaps,intents_volume_usd.

Regle dure : aucune donnee fictive. Si le CSV est absent, vide ou incomplet,
build() echoue proprement avec une exception explicite.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

try:
    from scripts.common import finalize_figure, read_daily_columns
except ImportError:  # execution directe : python scripts/xxx.py
    from common import finalize_figure, read_daily_columns

REQUIRED_COLUMNS = ("date", "active_accounts", "intents_volume_usd")


def _read_daily(daily_csv: str | Path) -> tuple[list[date], list[float], list[float]]:
    """Lit daily.csv (colonnes lot 08), trie par date. Echec propre sinon."""
    dates, values = read_daily_columns(
        daily_csv, REQUIRED_COLUMNS,
        missing_suffix=f". Colonnes requises : {', '.join(REQUIRED_COLUMNS)}.",
    )
    return dates, values["active_accounts"], values["intents_volume_usd"]


def _render(dates: list[date], actifs: list[float], volumes: list[float]):
    """Trace les deux series (double axe) et retourne la figure."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter

    fig, ax1 = plt.subplots(figsize=(10, 5.5))
    ax1.plot(dates, actifs, color="#1f77b4", linewidth=2, label="Comptes actifs")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Comptes actifs quotidiens", color="#1f77b4")
    ax1.tick_params(axis="y", labelcolor="#1f77b4")
    ax1.grid(True, alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(dates, volumes, color="#ff7f0e", linewidth=2, label="Volume Intents")
    ax2.set_ylabel("Volume Intents (USD)", color="#ff7f0e")
    ax2.tick_params(axis="y", labelcolor="#ff7f0e")
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"${v:,.0f}"))

    ax1.set_title("NEAR — Comptes actifs quotidiens vs volume Intents")
    fig.text(
        0.01,
        0.01,
        "Sources : bigquery-public-data.crypto_near_mainnet_us + "
        "Intents Explorer API (explorer.near-intents.org).",
        fontsize=7,
        color="gray",
        ha="left",
        va="bottom",
    )
    return fig


def build(daily_csv: str | Path, out_png: str | Path) -> Path:
    """Trace actifs quotidiens vs volume Intents (double axe) et sauve le PNG.

    Args:
        daily_csv: chemin vers data/merged/daily.csv.
        out_png: chemin de sortie, attendu charts/01_actifs_intents.png.

    Returns:
        Le chemin du PNG ecrit.

    Raises:
        FileNotFoundError: si le CSV source est absent.
        ValueError: si le CSV est vide, incomplet ou illisible.
    """
    dates, actifs, volumes = _read_daily(daily_csv)
    fig = _render(dates, actifs, volumes)
    return finalize_figure(fig, out_png)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Lot 08 : chart actifs vs Intents (double axe)."
    )
    parser.add_argument(
        "--daily",
        default="data/merged/daily.csv",
        help="Chemin du CSV fusionne (defaut : data/merged/daily.csv).",
    )
    parser.add_argument(
        "--out",
        default="charts/01_actifs_intents.png",
        help="PNG de sortie (defaut : charts/01_actifs_intents.png).",
    )
    args = parser.parse_args()
    written = build(args.daily, args.out)
    print(f"OK : {written}")
