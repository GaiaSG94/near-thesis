# Lot 01 — Inventaire tables BigQuery + fraîcheur

Dataset : `bigquery-public-data.crypto_near_mainnet_us`
Référence : https://docs.near.org/data-infrastructure/big-query

## 1. Tables attendues (à confirmer dans la console, aucun chiffre inventé)

| Table attendue | Usage prévu (lots suivants) | Statut |
|---|---|---|
| `transactions` | Lot 03 : `tx_count` quotidien via `block_date` | Attendue, à confirmer |
| `receipt_actions` | Lot 04 : `contract_calls`, `unique_contracts` via actions sur receipts | Attendue, à confirmer |
| `receipt_origin` **ou** `receipt_origin_transaction` | Jointure receipts → transaction d'origine si besoin (comptes actifs, attribution) | **Gap connu : trancher le vrai nom** |

Autres tables éventuellement présentes dans le dataset (blocks, receipts, execution_outcomes, etc.) : hors périmètre du lot 01, ne pas les requêter sans besoin d'un lot ultérieur.

## 2. Méthode de vérification des vrais noms (console BigQuery, sans coût)

1. Ouvrir https://console.cloud.google.com/bigquery
2. Dans l'explorateur, dérouler `bigquery-public-data` → `crypto_near_mainnet_us`.
3. Noter les noms exacts affichés : confirmer `transactions` et `receipt_actions`, puis trancher `receipt_origin` vs `receipt_origin_transaction` (une seule des deux existe probablement).
4. Pour chaque table, ouvrir l'onglet **Schéma** : vérifier la présence de la colonne `block_date` (colonne de partition / filtre obligatoire) et noter les colonnes utiles (`signer_account_id` attendu d'apres l'exemple officiel, `receiver_account_id` a confirmer, `transaction_hash` pour `transactions`).
5. Onglet **Détails** : noter la date de dernière modification (signal de fraîcheur gratuit, sans requête).
6. Exécuter ensuite `queries/00_sample.sql` requête par requête (jamais en une seule fois si un nom est incertain) :
   - sample `LIMIT 100` avec `WHERE block_date >= '2026-10-01'` ;
   - puis chaque `MAX(block_date)` en décommentant uniquement la variante dont la table existe.
7. Avant chaque exécution, lire l'estimateur « This query will process » en haut à droite (NEAR paie le stockage, le jury/l'exécutant paie les bytes scannés). Si le volume estimé est anormal, réduire les colonnes ou resserrer la fenêtre `block_date`.
8. Reporter dans ce fichier (section 3) : vrais noms constatés, `MAX(block_date)` observés, date de pull. Ne rien inventer : pas de valeur = laisser `non exécuté`.

## 3. Résultats constatés (à remplir après exécution, vide à la livraison du lot 01)

- `transactions` : existe = ?, `MAX(block_date)` = non exécuté
- `receipt_actions` : existe = ?, `MAX(block_date)` = non exécuté
- `receipt_origin` vs `receipt_origin_transaction` : tranché = non, retenu = ?
- Date de pull : non exécuté (BigQuery non exécuté sans credentials, conformément à la consigne)

## 4. Rappel fraîcheur post-Lake 24/03/2026

Lake déprécié le 24/03/2026 : si `MAX(block_date)` est antérieur à la date d'analyse ou stagne entre deux pulls, le noter dans `THESIS.md` (lot 13) comme limite de fraîcheur. Chaque pull ultérieur loggue : date de pull, bytes scannés, `MAX(block_date)` (contrat data de `intent.md`).
