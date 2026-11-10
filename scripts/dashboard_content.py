"""Lot 12 — Contenu statique du dashboard (extrait de build_dashboard.py).

Constantes purs (aucun import, aucun effet de bord) partagees par
l'orchestrateur ``build_dashboard.py`` et les modules ``dashboard_data``,
``dashboard_phrases`` et ``dashboard_render`` : textes maquette, ordre des
5 blocs, CSS inline. Contenu strictement identique a l'original.
"""

from __future__ import annotations

CLAIM = (
    "Hypothese : le volume cross-chain via NEAR Intents est un meilleur "
    "indicateur avance de l'usage reel que le prix."
)

# Prix du token hors sources imposees (intent.md) : aucune source prix
# versionnee n'existe dans ce depot, donc mention imposee. Modifiable si une
# source prix explicite et versionnee est ajoutee.
PRICE_NOTE = "non calculable depuis ces sources"

# Tailles des « top K » (choix de methode, affiches tels quels dans les phrases).
TOP_K_WALLETS = 10
TOP_K_CONTRACTS = 5

# Seuil de lecture phrase 4 : part du top K >= 50 % -> « peu » d'acteurs.
MANY_FEW_THRESHOLD_PCT = 50.0

# Cinq liens sources du footer (intent.md §Sources : navigation seule, aucune
# ressource distante chargee — la page reste entiere hors-ligne).
SOURCES_URLS: list[tuple[str, str]] = [
    ("Consigne these", "https://raw.githubusercontent.com/nearai/near-hackathon-prompt-examples/main/tracks/02-thesis.md"),
    ("BigQuery NEAR", "https://docs.near.org/data-infrastructure/big-query"),
    ("Donnees NEAR", "https://docs.near.org/data-infrastructure/what-is"),
    ("Explorer Intents", "https://docs.near-intents.org/integration/distribution-channels/1click-api/explorer/introduction"),
    ("API transactions", "https://docs.near-intents.org/integration/distribution-channels/1click-api/explorer/transactions"),
]

# ---------------------------------------------------------------------------
# Requetes exactes non-SQL (texte verbatim embarque tel quel dans le HTML).
# ---------------------------------------------------------------------------
INTENTS_REQUETE_EXACTE = """\
GET https://explorer.near-intents.org/api/v0/transactions
Parametres : statuses=SUCCESS
             startTimestamp=<debut de fenetre en ms epoch UTC>
             endTimestamp=<fin de fenetre en ms epoch UTC>
             direction=next (vers le plus vieux, defaut)
             numberOfTransactions=1000 (maximum autorise)
             lastDepositAddress=<curseur de pagination>
             lastDepositMemo=<curseur de pagination>
Authentification : Authorization: Bearer <JWT lu dans .env, jamais commite>
Cadence : 1 requete / 5 s minimum (erreur 429 si depassee)
Agregation (volume quotidien) : somme de amountInUsd des statuts SUCCESS,
regroupes par jour via createdAtTimestamp.
Implementation : scripts/fetch_intents.py (lot 06).
Brut conserve : data/raw/intents_*.json (enveloppes paginees, payload intact)."""

LEADLAG_DERIVATION_EXACTE = """\
Derivation depuis data/merged/daily.csv (lot 07), colonnes
active_accounts et intents_volume_usd :
  actifs(J)      = active_accounts du jour J
  volume(J - 7)  = intents_volume_usd sept jours plus tot
  volume(J - 14) = intents_volume_usd quatorze jours plus tot
Les decalages se calculent sur les dates du CSV fusionne ; les jours sans
anteriorite suffisante sont exclus de la comparaison, sans interpolation.
Correlation de Pearson sur les paires appariees (minimum 3 paires)."""

WALLETS_DERIVATION_EXACTE = """\
Derivation depuis le brut data/raw/intents_*.json (lot 06), alignee sur
scripts/chart_concentration.py (lot 11) pour que le % et le chart concordent :
  - ne garder que les transactions de statuts SUCCESS (controle defensif :
    le brut est deja filtre) ;
  - montant = premier champ renseigne parmi amountInUsd, amount_in_usd,
    inUsd, amountOutUsd, amount_out_usd, outUsd, strictement positif ;
  - adresse = premier champ renseigne parmi depositAddress,
    lastDepositAddress, fromAddress, sender, signer, address (puis
    deposit/from/sender.address) ;
  - sommer par adresse sur la fenetre, trier par volume decroissant ;
  - part du volume = volume cumule des premiers / volume total SUCCESS.
Aucune adresse n'est exclue ni fusionnee ; le brut reste la reference."""

DAILY_CONTRACT = """\
Contrat data/merged/daily.csv (intent.md, lot 07) :
  colonnes : date,active_accounts,tx_count,contract_calls,unique_contracts,
             intents_swaps,intents_volume_usd
  grain : 1 ligne / jour triee par date croissante.
  fenetre par defaut : block_date >= '2026-10-01' (plancher contractuel).
  Chaque pull loggue : date de pull, bytes scannes, MAX(block_date)."""

# Cle -> (titre affiche dans <details>, texte verbatim).
TEXT_SOURCES: dict[str, tuple[str, str]] = {
    "intents": ("Intents Explorer API — volume des swaps (lot 06)", INTENTS_REQUETE_EXACTE),
    "leadlag": ("Derivation lead-lag depuis daily.csv (lot 10)", LEADLAG_DERIVATION_EXACTE),
    "wallets": ("Derivation portefeuilles depuis le brut Intents (lot 11)", WALLETS_DERIVATION_EXACTE),
    "daily_contract": ("Contrat data/merged/daily.csv (lot 07)", DAILY_CONTRACT),
}

# ---------------------------------------------------------------------------
# Les 5 blocs, ordre maquette §2 inchange. Titres §7 : question factuelle
# courte suivie du sujet. sources : ("sql", "<fichier dans queries/>") ou
# ("text", <cle TEXT_SOURCES>). figures : liste (png, alt, legende) — le
# bloc 3 porte les 2 PNG du lot 09, le bloc 5 aucun (tableau §3).
# ---------------------------------------------------------------------------
BLOCKS: list[dict] = [
    {
        "id": "preuve",
        "title": "Les deux courbes bougent-elles ensemble ? — actifs quotidiens vs volume Intents",
        "toc": "1 Preuve",
        "lot": "lot 08 (scripts/chart_actifs.py)",
        "figures": [("01_actifs_intents.png",
                     "Courbes des comptes actifs quotidiens et du volume Intents sur la meme periode",
                     "Comptes actifs (axe gauche) et volume Intents (axe droit).")],
        "sources": [("sql", "01_active_accounts.sql"), ("text", "intents")],
    },
    {
        "id": "leadlag",
        "title": "Le volume précède-t-il l'usage ? — test J-7/J-14",
        "toc": "2 Lead-lag",
        "lot": "lot 10 (scripts/chart_leadlag.py)",
        "figures": [("04_leadlag.png",
                     "Volume Intents decale de sept et quatorze jours face aux comptes actifs du jour",
                     "Volume Intents J-7/J-14 realigne face aux actifs J.")],
        "sources": [("sql", "01_active_accounts.sql"), ("text", "intents"), ("text", "leadlag")],
    },
    {
        "id": "contexte",
        "title": "L'usage réel suit-il ? — transactions et contrats uniques",
        "toc": "3 Contexte",
        "lot": "lot 09 (scripts/chart_tx.py)",
        "figures": [("02_tx.png",
                     "Transactions quotidiennes du reseau",
                     "Transactions par jour."),
                    ("03_contrats.png",
                     "Contrats distincts appeles par jour",
                     "Contrats uniques par jour.")],
        "sources": [("sql", "02_tx_counts.sql"), ("sql", "03_contract_usage.sql"), ("sql", "04_top_contracts.sql")],
    },
    {
        "id": "limites",
        "title": "Le signal est-il fragile ? — concentration du volume (limites)",
        "toc": "4 Limites",
        "lot": "lot 11 (scripts/chart_concentration.py)",
        "warn": True,
        "figures": [("05_concentration.png",
                     "Principaux portefeuilles par volume et part cumulee du volume Intents",
                     "Part du volume par top adresses + courbe de concentration.")],
        "sources": [("text", "intents"), ("text", "wallets")],
    },
    {
        "id": "methode",
        "title": "Peut-on refaire le calcul ? — méthode et fraîcheur des données",
        "toc": "5 Méthode",
        "lot": "lots 01/05/07 (tableau, pas de PNG)",
        "figures": [],
        "sources": [("sql", "00_sample.sql"), ("text", "daily_contract")],
    },
]

# Lignes « Lecture jury » (§3, modifiables, sans chiffres) : une par bloc.
# Le bloc 4 porte « Ce que ça change au claim » au lieu d'une lecture neutre.
READINGS: dict[str, str] = {
    "preuve": "Lecture jury : les courbes se comparent visuellement ; une co-variation ne prouve pas une causalite.",
    "leadlag": "Lecture jury : une correlation plus forte avec decalage suggere un effet avance, sans le prouver ; plus faible, elle l'affaiblit.",
    "contexte": "Lecture jury : si l'activite on-chain stagne pendant que le volume Intents varie, le lien avec l'usage reel est douteux.",
    "limites": "Ce que ça change au claim : si peu de portefeuilles concentrent l'essentiel du volume, le signal mesure quelques acteurs, pas l'usage reel.",
    "methode": "Lecture jury : un chiffre sans requete ou log source ne compte pas — tout ici est re-calculable en une commande.",
}

# Verdict THESIS.md (lot 13) -> (classe CSS pastille, libelle affiche).
VERDICT_BADGES: dict[str, tuple[str, str]] = {
    "CONFIRMÉ": ("b-ok", "CONFIRMÉ"),
    "CONFIRME": ("b-ok", "CONFIRMÉ"),
    "NUANCÉ": ("b-nuance", "NUANCÉ"),
    "NUANCE": ("b-nuance", "NUANCÉ"),
    "INFIRMÉ": ("b-ko", "INFIRMÉ"),
    "INFIRME": ("b-ko", "INFIRMÉ"),
}
VERDICT_PENDING = ("b-pending", "NON FIGÉ (lot 13)")

# ---------------------------------------------------------------------------
# CSS inline, maquette §5 (palette inchangee, mise en forme etiree).
# Police systeme, aucune ressource distante, imprimable.
# ---------------------------------------------------------------------------
CSS_INLINE = """\
:root {
  --bg: #FAFAF7;
  --card: #FFFFFF;
  --ink: #1A1A18;
  --muted: #5C5A55;
  --line: #E3E0D8;
  --accent: #0B4F3A;
  --warn-bg: #FFF4E8;
  --warn-line: #C77B2E;
  --warn-ink: #8A4A00;
  --code: #F1EFEA;
}
body {
  background: var(--bg);
  color: var(--ink);
  font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  max-width: 960px;
  margin: 0 auto;
  padding: 24px;
  line-height: 1.55;
}
header, section.card, footer {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 20px 24px;
  margin-bottom: 20px;
}
header h1 { font-size: 1.4rem; margin: 0 0 8px; }
header p, footer p { margin: 4px 0; }
p.meta { color: var(--muted); font-size: 0.92em; }
nav.toc { margin-top: 10px; }
nav.toc a { color: var(--accent); margin-right: 12px; font-size: 0.9em; }
section.verdict h2 { color: var(--ink); }
section.warn { background: var(--warn-bg); border-color: var(--warn-line); }
section.warn h2 { color: var(--warn-ink); }
h2 { color: var(--accent); font-size: 1.15rem; margin-top: 0; }
img.chart {
  width: 100%;
  height: auto;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fff;
}
figcaption { font-size: 0.85rem; color: var(--muted); margin-top: 4px; }
p.fact { font-weight: 600; }
p.reading { color: var(--muted); font-size: 0.95em; }
details { margin-top: 12px; }
summary { cursor: pointer; color: var(--accent); font-weight: 600; }
pre {
  background: var(--code);
  padding: 12px;
  overflow-x: auto;
  border-radius: 6px;
  font-size: 0.85em;
  white-space: pre-wrap;
}
p.qlinks { font-size: 0.85em; }
p.qlinks a { color: var(--accent); margin-right: 10px; }
table.fresh { border-collapse: collapse; width: 100%; font-size: 0.92em; }
table.fresh td, table.fresh th {
  border: 1px solid var(--line);
  padding: 6px 10px;
  text-align: left;
}
table.fresh th { width: 34%; color: var(--muted); font-weight: 600; }
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-weight: 700;
  font-size: 0.85em;
}
.b-ok { color: #0B4F3A; background: #E4EFE9; border: 1px solid #0B4F3A; }
.b-nuance { color: #8A4A00; background: #FFF4E8; border: 1px solid #C77B2E; }
.b-ko { color: #8B1E1E; background: #F9E9E9; border: 1px solid #8B1E1E; }
.b-pending { color: #5C5A55; background: #EFEDE8; border: 1px solid #B9B5AB; }
footer nav.src a { color: var(--accent); margin-right: 10px; font-size: 0.85em; }
@media print {
  body { background: #fff; }
  section.warn { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
"""
