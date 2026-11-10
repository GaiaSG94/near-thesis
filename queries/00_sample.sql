-- NEAR Thesis — Lot 01 : sample query + fraîcheur
-- Dataset : `bigquery-public-data.crypto_near_mainnet_us`
-- Fenêtre par défaut imposée : block_date >= '2026-10-01'
-- Lake déprécié le 24/03/2026 : toujours vérifier MAX(block_date) avant d'interpréter.

-- 1) Sample query : 100 transactions récentes (colonnes minimales, partition block_date filtrée)
SELECT
  block_date,
  block_height,
  transaction_hash,
  signer_account_id, -- aligne sur l'exemple officiel docs.near.org (a confirmer dans l'onglet Schema)
  receiver_account_id -- a confirmer dans l'onglet Schema (variante possible : receiver_id)
FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date >= '2026-10-01'
ORDER BY block_date DESC, block_height DESC
LIMIT 100;

-- 2) Fraîcheur post-Lake : MAX(block_date) par table attendue
-- Exécuter séparément si une table n'existe pas (voir docs/tables.md pour trancher les noms).
SELECT 'transactions' AS table_name, MAX(block_date) AS max_block_date, COUNT(*) AS row_count_sample_window
FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date >= '2026-10-01';

-- SELECT 'receipt_actions' AS table_name, MAX(block_date) AS max_block_date, COUNT(*) AS row_count_sample_window
-- FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_actions`
-- WHERE block_date >= '2026-10-01';

-- Gap connu : le nom exact de la table d'origine des receipts est à trancher
-- dans la console (receipt_origin vs receipt_origin_transaction). Décommenter
-- la variante qui existe réellement :
-- SELECT 'receipt_origin' AS table_name, MAX(block_date) AS max_block_date
-- FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_origin`
-- WHERE block_date >= '2026-10-01';
-- SELECT 'receipt_origin_transaction' AS table_name, MAX(block_date) AS max_block_date
-- FROM `bigquery-public-data.crypto_near_mainnet_us.receipt_origin_transaction`
-- WHERE block_date >= '2026-10-01';
