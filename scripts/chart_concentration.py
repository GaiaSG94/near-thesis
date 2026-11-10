"""Lot 11 — Chart concentration du volume Intents (contre-preuve).

Lit le brut `data/raw/intents_*.json` (lot 06) et produit
`charts/05_concentration.png` : part du volume par top adresses +
courbe de concentration.

Contre-preuve visee : si l'essentiel du volume Intents provient d'une
poignee d'adresses (whales, market-makers, bots), alors le volume mesure
l'activite de quelques acteurs et non un usage large — ce qui affaiblit
l'hypothese « le volume cross-chain via NEAR Intents est un meilleur
indicateur avance de l'usage reel que le prix ».

Regle dure : aucune donnee fictive. Sans brut par transaction, la
concentration n'est pas calculable : `data/merged/daily.csv` est agrege
(pas de detail par adresse) et ne peut pas servir de repli — build()
echoue alors proprement avec une exception explicite.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

try:
    from scripts.common import (
        INTENTS_ADDRESS_KEYS,
        INTENTS_VOLUME_KEYS,
        extract_envelope_items,
        tx_address,
        tx_status_ok,
        tx_volume_usd,
    )
except ImportError:  # execution directe : python scripts/xxx.py
    from common import (
        INTENTS_ADDRESS_KEYS,
        INTENTS_VOLUME_KEYS,
        extract_envelope_items,
        tx_address,
        tx_status_ok,
        tx_volume_usd,
    )

RAW_GLOB = "intents_*.json"

# Listes canoniques (voir scripts/common.py) : entree puis sortie.
_VOLUME_KEYS = INTENTS_VOLUME_KEYS
_ADDRESS_KEYS = INTENTS_ADDRESS_KEYS


def _extract_items(envelope: dict | list) -> list[dict]:
    """Extrait la liste des transactions d'un fichier brut (lot 06)."""
    return extract_envelope_items(envelope)


def _tx_status_ok(tx: dict) -> bool:
    """Ne garde que les SUCCESS (le brut est deja filtre, controle defensif)."""
    return tx_status_ok(tx)


def _tx_volume(tx: dict) -> float | None:
    """Montant USD strictement positif d'une transaction, ou None."""
    return tx_volume_usd(tx)


def _tx_address(tx: dict) -> str | None:
    """Adresse de depot (ou expediteur) d'une transaction, ou None."""
    return tx_address(tx)


def _load_volumes_by_address(raw_dir: str | Path) -> tuple[dict[str, float], int, int]:
    """Agrege le volume USD par adresse depuis le brut.

    Returns:
        (volumes_par_adresse, nb_fichiers_lus, nb_tx_retenues).
    """
    raw_path = Path(raw_dir)
    files = sorted(glob.glob(str(raw_path / RAW_GLOB)))
    if not files:
        daily_hint = Path("data/merged/daily.csv")
        try:
            daily_hint = raw_path.parent.parent / "data" / "merged" / "daily.csv"
        except Exception:
            pass
        raise FileNotFoundError(
            f"Aucun brut Intents ({RAW_GLOB}) dans {raw_path}. "
            "Lancez d'abord le lot 06 (scripts/fetch_intents.py) pour produire "
            "data/raw/intents_*.json. La concentration exige le detail par "
            "transaction : data/merged/daily.csv est agrege (pas de detail par "
            "adresse) et ne permet pas ce calcul. Aucune donnee fictive generee."
        )
    volumes: dict[str, float] = {}
    kept = 0
    for fname in files:
        try:
            envelope = json.loads(Path(fname).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"Fichier brut illisible : {fname} ({exc}).") from exc
        if not isinstance(envelope, (dict, list)):
            continue
        for tx in _extract_items(envelope):
            if not _tx_status_ok(tx):
                continue
            amount = _tx_volume(tx)
            addr = _tx_address(tx)
            if amount is None or addr is None:
                continue
            volumes[addr] = volumes.get(addr, 0.0) + amount
            kept += 1
    if not volumes:
        raise ValueError(
            f"{len(files)} fichier(s) brut(s) lus dans {raw_path} mais aucune "
            "transaction exploitable (adresse + montant USD > 0 avec statut "
            "SUCCESS). Verifiez le format du brut du lot 06. Aucune donnee "
            "fictive generee."
        )
    return volumes, len(files), kept


def _short(addr: str, head: int = 6, tail: int = 4) -> str:
    if len(addr) <= head + tail + 3:
        return addr
    return f"{addr[:head]}...{addr[-tail:]}"


def _ranked_shares(volumes: dict[str, float]) -> tuple[list, list[float], list[float]]:
    """Trie par volume decroissant, calcule parts et cumul."""
    ranked = sorted(volumes.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(v for _, v in ranked)
    shares = [v / total for _, v in ranked]
    cumul = []
    running = 0.0
    for s in shares:
        running += s
        cumul.append(running)
    return ranked, shares, cumul


def _bars_panel(ax1, ranked: list, shares: list[float], top_n: int) -> None:
    """Panneau gauche : barres horizontales du top N (plus gros en haut)."""
    from matplotlib.ticker import FuncFormatter

    top_n = min(top_n, len(ranked))
    top_addrs = ranked[:top_n]
    top_shares = shares[:top_n]
    labels = [_short(a) for a, _ in reversed(top_addrs)]
    values = [s * 100 for s in reversed(top_shares)]
    ax1.barh(labels, values, color="#d62728")
    ax1.set_xlabel("Part du volume total (%)")
    ax1.set_title(f"Part du volume — top {top_n} adresses")
    ax1.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: f"{v:.1f}%"))
    for i, v in enumerate(values):
        ax1.text(v, i, f" {v:.1f}%", va="center", fontsize=8)


def _curve_panel(ax2, shares: list[float], cumul: list[float]) -> None:
    """Panneau droit : courbe de concentration (% adresses -> % cumule)."""
    n_addr = len(shares)
    xs = [(k + 1) / n_addr * 100 for k in range(n_addr)]
    ys = [c * 100 for c in cumul]
    ax2.plot(xs, ys, color="#d62728", linewidth=2, label="Volume cumule observe")
    ax2.plot([0, 100], [0, 100], color="gray", linestyle="--", linewidth=1,
             label="Egalite parfaite")
    ax2.set_xlabel("% des adresses (triees, plus grosses d'abord)")
    ax2.set_ylabel("% cumule du volume")
    ax2.set_title("Courbe de concentration")
    ax2.set_xlim(0, 100)
    ax2.set_ylim(0, 100)
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8, loc="lower right")
    top1 = shares[0] * 100
    top10 = cumul[min(10, n_addr) - 1] * 100
    ax2.text(
        0.97, 0.05,
        f"Top 1 : {top1:.1f}% du volume\nTop 10 : {top10:.1f}% du volume",
        transform=ax2.transAxes, ha="right", va="bottom", fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )


def _render(ranked: list, shares: list[float], cumul: list[float], top_n: int,
            n_files: int, n_tx: int, out_png: str | Path) -> Path:
    """Assemble les deux panneaux, annote, sauve le PNG, ferme."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_addr = len(ranked)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5.5))
    _bars_panel(ax1, ranked, shares, top_n)
    _curve_panel(ax2, shares, cumul)

    fig.suptitle("NEAR Intents — Concentration du volume par adresse (contre-preuve)")
    fig.text(
        0.01, 0.01,
        f"Sources : brut Intents Explorer API ({n_files} fichier(s), {n_tx} tx, "
        f"{n_addr} adresses). Lecture : plus la courbe s'ecarte de la diagonale, "
        "plus le volume vient de quelques adresses — ce qui affaiblit "
        "l'hypothese d'un indicateur d'usage large.",
        fontsize=7, color="gray", ha="left", va="bottom", wrap=True,
    )
    fig.tight_layout()

    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def build(
    raw_dir: str | Path = "data/raw",
    out_png: str | Path = "charts/05_concentration.png",
    top_n: int = 10,
) -> Path:
    """Trace la concentration du volume et sauve le PNG.

    Args:
        raw_dir: dossier du brut lot 06 (data/raw/intents_*.json).
        out_png: chemin de sortie, attendu charts/05_concentration.png.
        top_n: nombre d'adresses du panneau barres (defaut 10).

    Returns:
        Le chemin du PNG ecrit.

    Raises:
        FileNotFoundError: si le brut data/raw/intents_*.json est absent.
        ValueError: si le brut ne contient aucune transaction exploitable.
    """
    if top_n < 1:
        raise ValueError(f"top_n doit valoir au moins 1 (recu {top_n}).")
    volumes, n_files, n_tx = _load_volumes_by_address(raw_dir)
    ranked, shares, cumul = _ranked_shares(volumes)
    return _render(ranked, shares, cumul, top_n, n_files, n_tx, out_png)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Lot 11 : chart concentration du volume (contre-preuve)."
    )
    parser.add_argument(
        "--raw",
        default="data/raw",
        help="Dossier du brut lot 06 (defaut : data/raw).",
    )
    parser.add_argument(
        "--out",
        default="charts/05_concentration.png",
        help="PNG de sortie (defaut : charts/05_concentration.png).",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Nombre d'adresses du panneau barres (defaut : 10).",
    )
    args = parser.parse_args()
    written = build(args.raw, args.out, args.top)
    print(f"OK : {written}")
