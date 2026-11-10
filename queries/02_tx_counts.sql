-- Lot 03 — query-tx : nombre de transactions par jour (NEAR mainnet).
-- Source : bigquery-public-data.crypto_near_mainnet_us.transactions
-- Contrat data : alimente la colonne `tx_count` de data/merged/daily.csv
--   (grain : 1 ligne / jour, colonne date = block_date).
--
-- NOTE COUT (BigQuery) :
--   - NEAR paie le stockage, le jury paie les bytes scannes par cette requete.
--   - Le filtre `block_date >= '2026-10-01'` sur la partition est OBLIGATOIRE :
--     ne jamais l'enlever ni l'elargir sans besoin, sinon la requete scanne
--     tout l'historique.
--   - Colonnes minimales : seul `block_date` est lu (COUNT(*) ne lit aucune
--     colonne supplementaire). Ne pas passer en SELECT *.
--   - Avant execution : estimer avec un dry run (bq --dry_run) et logguer
--     bytes scannes + MAX(block_date) constate, jamais de chiffre invente.
--   - Fraicheur (Lake deproche le 24/03/2026) : verifier MAX(block_date)
--     via le lot 01 (queries/00_sample.sql), pas ici.
--
-- Fenetre par defaut (contrat fixe) : block_date >= '2026-10-01'.
-- Si le dataset reel n'expose pas `block_date` mais `block_timestamp`,
-- remplacer `block_date` par `DATE(block_timestamp)` dans SELECT / WHERE /
-- GROUP BY (tranche par le lot 01 sur le dataset reel).

SELECT
  block_date AS date,
  COUNT(*) AS tx_count
FROM
  `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE
  block_date >= '2026-10-01'
GROUP BY
  block_date
ORDER BY
  date ASC;
