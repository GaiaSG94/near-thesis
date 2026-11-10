-- ============================================================================
-- NEAR Thesis — Lot 04 : top contrats par volume d'appels
-- Fichier : near-thesis/queries/04_top_contracts.sql
-- Usage   : concentration de l'usage (quel contrat capte les appels
--           FUNCTION_CALL sur la fenetre). Eclaire la chart-concentration.
-- Dataset : bigquery-public-data.crypto_near_mainnet_us
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
-- - LIMIT 50 : borne basse cout, suffisante pour la concentration. Tri
--   deterministe (appels DESC, contrat ASC) pour des pulls reproductibles.
-- - Lake deprecie le 24/03/2026 : verifier MAX(block_date) et noter la
--   fraicheur dans THESIS.md (pas de chiffre invente ici).
-- ============================================================================

SELECT
  ra.receipt_receiver_account_id AS contract_id,
  COUNT(*) AS contract_calls,
  COUNT(DISTINCT ra.block_date) AS active_days
FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions` AS ra
WHERE
  ra.action_kind = 'FUNCTION_CALL'
  AND ra.block_date >= DATE '2026-10-01'
GROUP BY
  ra.receipt_receiver_account_id
ORDER BY
  contract_calls DESC,
  contract_id ASC
LIMIT 50;
