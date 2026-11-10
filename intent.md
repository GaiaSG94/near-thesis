# NEAR Thesis — Plan d'exécution (intent.md)

## Objectif
Tester l'hypothèse « le volume cross-chain via NEAR Intents est un meilleur
indicateur avancé de l'usage réel que le prix » avec une preuve 100%
reproductible par le jury. Dossier d'implémentation : `near-thesis/`.

## Les 5 livrables imposés
1. SQL BigQuery sur `bigquery-public-data.crypto_near_mainnet_us` :
   comptes actifs quotidiens, transactions, usage contrats. Filtre
   `block_date` obligatoire partout.
2. Pull Intents Explorer API pour le volume de swaps. JWT en `.env`,
   jamais commité. `.env.example` commité sans secret.
3. Une commande unique `python rebuild.py` qui refait tout depuis le brut.
4. Page statique `dashboard.html` : chaque chart + sa requête exacte +
   une phrase factuelle. Ouvrable en double-clic hors-ligne.
5. `THESIS.md` : claim, preuves pour, preuves contre, seuil qui ferait
   changer d'avis. Règle dure : Never invent numbers.

## Règles dures vérifiées
- Base Intents : `https://explorer.near-intents.org/api/v0`,
  `GET /transactions`, JWT requis, 1 req / 5 s, 429 si dépassé.
- Pagination curseur : `lastDepositAddress` + `lastDepositMemo`,
  `direction=next` (plus vieux, défaut), `numberOfTransactions` max 1000.
- Volume = somme `amountInUsd` (ou `amountOutUsd`) des `statuses=SUCCESS`
  par jour via `createdAtTimestamp`. Ancien param
  `lastDepositAddressAndMemo` déprécié.
- BigQuery : NEAR paie le stockage, toi les queries. Ne sélectionner que
  les colonnes et la partition `block_date` utiles.
- Lake déprécié le 24/03/2026 : vérifier `MAX(block_date)` dès la sample
  query et noter la fraîcheur dans THESIS.md.
- Prix du token hors sources imposées : soit source prix explicite et
  versionnée, soit mention « non calculable depuis ces sources ».
- Première étape imposée : lister les tables + 1 sample query, puis pause.

## Architecture cible
    near-thesis/
      intent.md (copie de ce fichier)
      queries/*.sql
      scripts/fetch_bigquery.py
      scripts/fetch_intents.py
      scripts/build_charts.py
      scripts/build_dashboard.py
      rebuild.py
      data/raw/ + data/merged/daily.csv
      charts/*.png
      dashboard.html
      THESIS.md README.md .env.example requirements.txt

## Contrat data (fixe, ne pas changer sans accord)
`data/merged/daily.csv` : `date,active_accounts,tx_count,contract_calls,
unique_contracts,intents_swaps,intents_volume_usd`.
Fenêtre par défaut : `block_date >= '2026-10-01'`.
Chaque pull loggue : date de pull, bytes scannés, MAX(block_date).

## Répartition Baptiste / moi (relecture et intégration)
- Baptiste (data) : lots 01-07.
- Moi (preuve + visuel) : lots 08-14 + discussion visuelle.

## Les 14 lots (un sous-agent par lot, fichiers disjoints)
- 01 tables-fraicheur : inventaire tables BigQuery + `MAX(block_date)` +
  `queries/00_sample.sql`. Gap connu : `receipt_origin` vs
  `receipt_origin_transaction` à trancher dans le dataset réel.
- 02 query-actifs : `queries/01_active_accounts.sql`.
- 03 query-tx : `queries/02_tx_counts.sql`.
- 04 query-contrats : `queries/03_contract_usage.sql` + top contrats.
- 05 fetch-bigquery : `scripts/fetch_bigquery.py` + logs coûts.
- 06 fetch-intents : `scripts/fetch_intents.py`, throttle 5 s, cache brut
  `data/raw/intents_*.json`, filtres SUCCESS + timestamps.
- 07 merge-rebuild : merge `data/merged/daily.csv` + squelette `rebuild.py`.
- 08 chart-actifs-intents : PNG double axe + fonction dédiée.
- 09 chart-tx-contrats : PNG transactions + contrats uniques.
- 10 chart-leadlag : PNG Intents J-7/J-14 vs actifs J.
- 11 chart-concentration : PNG top wallets + part du volume.
- 12 dashboard : `scripts/build_dashboard.py` → `dashboard.html` inline,
  zéro dépendance réseau, 1 chart = 1 requête = 1 phrase.
- 13 thesis : `THESIS.md` complet avec liens vers chaque requête.
- 14 packaging : `requirements.txt` pinné, `README.md`, `.env.example`,
  validation jury (rebuild avec et sans JWT, HTML offline).

## Mission visuelle (agent 15, discussion en amont)
Proposer la maquette la plus judicieuse pour convaincre le jury :
ordre des blocs, 5 phrases factuelles types (sans chiffres inventés),
structure HTML/CSS inline, wireframe textuel des éléments de page.
Discuter avec le parent avant que le lot 12 fige le HTML.

## Validation jury
- `pip install -r requirements.txt` puis `python rebuild.py` : OK.
- Rebuild sans `.env` via `data/raw/` : mêmes chiffres.
- `dashboard.html` Wi-Fi coupé : 5 visuels + requêtes + phrases.
- Chaque SQL contient `block_date`. `.env` absent de git.
- Chaque chiffre de THESIS.md pointe vers une requête ou un log.

## Sources
- https://raw.githubusercontent.com/nearai/near-hackathon-prompt-examples/main/tracks/02-thesis.md
- https://docs.near.org/data-infrastructure/big-query
- https://docs.near.org/data-infrastructure/what-is
- https://docs.near-intents.org/integration/distribution-channels/1click-api/explorer/introduction
- https://docs.near-intents.org/integration/distribution-channels/1click-api/explorer/transactions
