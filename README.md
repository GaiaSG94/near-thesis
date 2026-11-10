# NEAR Thesis — preuve reproductible par le jury

Hypothèse : « le volume cross-chain via NEAR Intents est un meilleur
indicateur avancé de l'usage réel que le prix ».
Plan d'exécution : [intent.md](intent.md). Thèse : [THESIS.md](THESIS.md).

## 1. Installation

```bash
cd near-thesis
python -m pip install -r requirements.txt
```

Python requis : >= 3.10.

## 2. Rebuild complet (avec JWT — rafraîchit le brut)

```bash
cp .env.example .env
# Éditer .env : coller le JWT dans NEAR_INTENTS_JWT (jamais commité).
python rebuild.py
```

`rebuild.py` refait tout depuis le brut : pulls BigQuery + Intents,
`data/merged/daily.csv`, charts PNG, `dashboard.html`.
Chaque pull loggue : date de pull, bytes scannés, `MAX(block_date)`.

## 3. Rebuild sans JWT (mode cache — mêmes chiffres)

```bash
python rebuild.py
```

Sans `.env`, le rebuild réutilise le brut versionné `data/raw/`
(`intents_*.json` + exports BigQuery) et produit les mêmes chiffres,
sans aucun appel réseau authentifié.

## 4. Dashboard hors-ligne

Ouvrir `dashboard.html` en double-clic (Wi-Fi coupé : OK).
Zéro dépendance réseau : chaque chart embarque sa requête SQL exacte
et une phrase factuelle. Règle dure : Never invent numbers.

## 5. Contrôles jury

- Chaque SQL de `queries/` contient un filtre `block_date`.
- `.env` absent de git (seul `.env.example`, sans secret, est commité).
- Chaque chiffre de `THESIS.md` pointe vers une requête ou un log.
- Fenêtre par défaut : `block_date >= '2026-10-01'`.
- Contrat data : `data/merged/daily.csv` =
  `date,active_accounts,tx_count,contract_calls,unique_contracts,intents_swaps,intents_volume_usd`.
