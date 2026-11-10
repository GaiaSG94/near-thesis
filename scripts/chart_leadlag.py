"""Lot 10 — chart lead-lag : volume Intents J-7 / J-14 vs comptes actifs J.

Entree : data/merged/daily.csv (contrat fixe : date,active_accounts,tx_count,
    contract_calls,unique_contracts,intents_swaps,intents_volume_usd).
Sortie : charts/04_leadlag.png

Hypothese testee : le volume Intents est un indicateur AVANCE de l'usage
reel. Si c'est vrai, un pic d'Intents a J-7 (ou J-14) doit coincider avec
un pic de comptes actifs a J une fois les series realignees.

METHODE DE DECALAGE (lead-lag par realignement) :
  1. daily.csv est trie par date croissante (grain : 1 ligne = 1 jour
     calendaire). Aucun reechantillonnage, aucune interpolation.
  2. Pour chaque date J :
       - actifs(J)      = active_accounts lu a la ligne J (pas de decalage) ;
       - intents(J-7)   = intents_volume_usd lu 7 lignes plus tot, reaffiche
                          en face de J (pandas Series.shift(7)) ;
       - intents(J-14)  = intents_volume_usd lu 14 lignes plus tot, reaffiche
                          en face de J (pandas Series.shift(14)).
     Autrement dit on translate le passe des Intents VERS le present des
     actifs pour comparer visuellement les pics au meme abscisse J.
  3. Les 7 (resp. 14) premieres valeurs decalees sont NaN et ne sont PAS
     tracees : aucun remplissage (ni zero, ni forward-fill), conformement a
     la regle "Never invent numbers". Seules des observations reelles
     decalees apparaissent sur le chart.
  4. Historique minimum : 15 jours calendaires distincts. En dessous,
     la serie J-14 n'aurait aucun point exploitable avec du contexte,
     donc build() leve ValueError et aucun PNG n'est ecrit (echec propre).

Lecture du chart : si les pics pointilles (Intents decales, axe droit)
  precedent ou coincident avec les pics pleins (actifs J, axe gauche),
  c'est un signal visuel que le volume Intents avance l'usage ; sinon,
  preuve contre l'hypothese (a consigner dans THESIS.md).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # Backend non-interactif : rebuild.py tourne sans ecran.
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd

MIN_DAYS = 15  # Seuil d'echec propre : historique < 15 jours -> ValueError.
SHIFT_7 = 7
SHIFT_14 = 14

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "merged" / "daily.csv"
DEFAULT_OUTPUT = REPO_ROOT / "charts" / "04_leadlag.png"

REQUIRED_COLUMNS = {"date", "active_accounts", "intents_volume_usd"}


def _load_daily(input_csv: Path) -> pd.DataFrame:
    """Lit et valide daily.csv. Ne cree jamais de donnees."""
    if not input_csv.is_file():
        raise FileNotFoundError(
            f"Introuvable : {input_csv}. "
            "Executer d'abord le lot 07 (merge -> data/merged/daily.csv)."
        )
    df = pd.read_csv(input_csv, parse_dates=["date"])
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans {input_csv} : {sorted(missing)}. "
            "Contrat attendu : date,active_accounts,intents_volume_usd "
            "(+ tx_count,contract_calls,unique_contracts,intents_swaps)."
        )
    df = df.sort_values("date").drop_duplicates(subset="date").reset_index(drop=True)
    n_days = df["date"].nunique()
    if len(df) < MIN_DAYS or n_days < MIN_DAYS:
        raise ValueError(
            f"Historique insuffisant : {len(df)} lignes / {n_days} jours distincts "
            f"dans {input_csv}, minimum requis {MIN_DAYS} jours pour tracer "
            "la serie J-14 avec du contexte. Aucun PNG ecrit, aucune donnee "
            "fictive generee."
        )
    return df


def _compute_lags(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Decale le passe des Intents face au present des actifs (NaN gardes)."""
    # Le passe des Intents est re-affiche en face du present des actifs
    # (voir docstring du module). Les NaN de tete sont laisses tels quels :
    # matplotlib les omet, sans invention de points.
    lag7 = df["intents_volume_usd"].shift(SHIFT_7)
    lag14 = df["intents_volume_usd"].shift(SHIFT_14)
    return lag7, lag14


def _plot_lines(df: pd.DataFrame, lag7: pd.Series, lag14: pd.Series) -> tuple:
    """Trace actifs J (plein) + Intents decales (pointilles), double axe."""
    fig, ax_left = plt.subplots(figsize=(11, 6))
    (line_actifs,) = ax_left.plot(
        df["date"],
        df["active_accounts"],
        color="C0",
        linewidth=2,
        label="Comptes actifs (J)",
    )
    ax_left.set_xlabel("Date (J)")
    ax_left.set_ylabel("Comptes actifs quotidiens (J)", color="C0")
    ax_left.tick_params(axis="y", labelcolor="C0")
    ax_left.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_left.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
    fig.autofmt_xdate(rotation=30, ha="right")

    ax_right = ax_left.twinx()
    (line_lag7,) = ax_right.plot(
        df["date"],
        lag7,
        color="C1",
        linewidth=1.5,
        linestyle="--",
        label="Volume Intents J-7 (USD, realigne sur J)",
    )
    (line_lag14,) = ax_right.plot(
        df["date"],
        lag14,
        color="C2",
        linewidth=1.5,
        linestyle=":",
        label="Volume Intents J-14 (USD, realigne sur J)",
    )
    ax_right.set_ylabel("Volume Intents decale (USD)", color="black")

    ax_left.set_title(
        "Lead-lag : volume Intents J-7 / J-14 vs comptes actifs J\n"
        f"({df['date'].min().date()} au {df['date'].max().date()}, "
        f"{len(df)} jours ; series Intents decalees de {SHIFT_7} et {SHIFT_14} j)"
    )
    ax_left.grid(True, alpha=0.3)
    return fig, ax_left, [line_actifs, line_lag7, line_lag14]


def _finish(fig, ax_left, lines, output_png: Path) -> Path:
    """Legende combinee, mise en page, sauvegarde PNG, fermeture."""
    # Legende combinee des deux axes, explicite sur le sens du decalage.
    ax_left.legend(
        lines,
        [line.get_label() for line in lines],
        loc="upper left",
        fontsize=9,
        framealpha=0.9,
    )
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=150)
    plt.close(fig)
    return output_png


def build(
    input_csv: Path | str = DEFAULT_INPUT,
    output_png: Path | str = DEFAULT_OUTPUT,
) -> Path:
    """Construit charts/04_leadlag.png depuis data/merged/daily.csv.

    Leve FileNotFoundError (CSV absent) ou ValueError (colonnes manquantes
    ou historique < 15 jours). En cas d'echec, aucun fichier n'est ecrit.
    """
    input_csv = Path(input_csv)
    output_png = Path(output_png)
    df = _load_daily(input_csv)
    lag7, lag14 = _compute_lags(df)
    fig, ax_left, lines = _plot_lines(df, lag7, lag14)
    return _finish(fig, ax_left, lines, output_png)


def main() -> int:
    try:
        written = build(DEFAULT_INPUT, DEFAULT_OUTPUT)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERREUR chart lead-lag : {exc}", file=sys.stderr)
        return 1
    print(f"OK chart lead-lag : {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
