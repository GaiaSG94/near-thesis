-- ============================================================================
-- NEAR Thesis — Lot 04 : usage contrats (quotidien)
-- Fichier : near-thesis/queries/03_contract_usage.sql
-- Alimente : data/merged/daily.csv -> colonnes contract_calls, unique_contracts
-- Dataset  : bigquery-public-data.crypto_near_mainnet_us
-- ============================================================================
-- COUT / PARTITIONS (lire avant d'executer) :
-- - NEAR paie le stockage, l'executant paie les bytes scannes (facturation
--   BigQuery on-demand, 1 To/mois gratuit). Ne selectionner que les colonnes
--   utiles ci-dessous (block_date, receipt_receiver_account_id, action_kind).
-- - Filtre OBLIGATOIRE sur la colonne de partition block_date (toujours present
--   dans le WHERE) pour limiter le scan. Fenetre par defaut du contrat data :
--   block_date >= '2026-10-01'. Ne pas l'elargir sans accord.
-- - Avant RUN : verifier l'estimation ("This query will process ...") dans la
--   console BigQuery ou via dry-run (scripts/fetch_bigquery.py).
-- - A chaque pull, logguer : date de pull, bytes scannes, MAX(block_date).
-- - Lake deprecie le 24/03/2026 : verifier MAX(block_date) et noter la
--   fraicheur dans THESIS.md (pas de chiffre invente ici).
-- ============================================================================

SELECT
  ra.block_date AS date,
  COUNT(*) AS contract_calls,
  COUNT(DISTINCT ra.receipt_receiver_account_id) AS unique_contracts
FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions` AS ra
WHERE
  ra.action_kind = 'FUNCTION_CALL'
  AND ra.block_date >= DATE '2026-10-01'
GROUP BY
  ra.block_date
ORDER BY
  ra.block_date ASC;
