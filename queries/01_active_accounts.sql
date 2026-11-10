-- Lot 02 — Comptes actifs quotidiens (NEAR Thesis).
-- Dataset : `bigquery-public-data.crypto_near_mainnet_us.transactions`.
-- Définition : un compte actif un jour donné = un `signer_account_id` distinct
-- observé ce `block_date` (cf. exemple officiel docs.near.org/data-infrastructure/big-query).
-- Fenêtre par défaut du contrat : block_date >= '2026-10-01'.
-- Colonnes minimales : block_date + signer_account_id uniquement.
--
-- Coût attendu : NEAR paie le stockage, les requêtes restent à ta charge.
-- Vérifier l'estimation affichée par BigQuery (octets analysés) avant d'exécuter ;
-- ne sélectionner que les colonnes et la partition block_date utiles.
-- Aucun montant n'est indiqué ici : se référer à la grille BigQuery en vigueur.
--
-- Fraîcheur (Lake déprécié le 24/03/2026, vérifier avant d'interpréter) :
--   SELECT MAX(block_date) AS max_block_date
--   FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`;
-- Noter la valeur obtenue (date de pull + MAX(block_date)) dans les logs / THESIS.md.
SELECT
  block_date AS date,
  COUNT(DISTINCT signer_account_id) AS active_accounts
FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date >= DATE '2026-10-01'
GROUP BY date
ORDER BY date;
