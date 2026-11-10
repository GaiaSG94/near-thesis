# THESIS.md — NEAR Intents comme indicateur avancé de l'usage réel

> Règle dure : aucun chiffre inventé. Toute valeur mesurée est un placeholder
> `[À remplir après rebuild → …]` à compléter par `python rebuild.py`.
> Fenêtre par défaut : `block_date >= '2026-10-01'` (contrat data fixe).

## 1. Claim (3 lignes)

1. Le volume cross-chain via NEAR Intents est un meilleur indicateur avancé de l'usage réel (comptes actifs, appels contrats) que le prix du token.
2. Concrètement : le volume Intents à J−7/J−14 prédit les comptes actifs à J mieux qu'une baseline naïve (persistance) et que le prix.
3. Si cette avance prédictive n'existe pas sur la fenêtre mesurée, la thèse est rejetée (voir §5 seuil d'invalidation).

## 2. Preuves POUR (à remplir après rebuild, corrélations datées)

Chaque ligne : valeur + date de pull + source exacte. Rebuild : `python rebuild.py` → `data/merged/daily.csv`
(`date,active_accounts,tx_count,contract_calls,unique_contracts,intents_swaps,intents_volume_usd`).

| # | Fait mesuré | Valeur (placeholder) | Pull / fenêtre | Source |
|---|-------------|----------------------|----------------|--------|
| P1 | Corrélation Pearson volume Intents (J−7) vs comptes actifs (J) | [À remplir après rebuild → `data/merged/daily.csv`, colonnes `intents_volume_usd` vs `active_accounts`] | Pull du [À remplir → log `scripts/fetch_bigquery.py`] ; fenêtre [À remplir → `MAX(block_date)` constaté] | [01_active_accounts.sql](queries/01_active_accounts.sql) + `scripts/fetch_intents.py` (`GET /transactions`, `statuses=SUCCESS`, somme `amountInUsd` par jour via `createdAtTimestamp`) |
| P2 | Corrélation Pearson volume Intents (J−14) vs comptes actifs (J) | [À remplir après rebuild → `data/merged/daily.csv`] | Pull du [À remplir → log] ; n = [À remplir → nombre de jours] jours | [01_active_accounts.sql](queries/01_active_accounts.sql) + `scripts/fetch_intents.py` |
| P3 | Corrélation contemporaine (J vs J) volume Intents vs comptes actifs | [À remplir après rebuild → `data/merged/daily.csv`] | Idem | [01_active_accounts.sql](queries/01_active_accounts.sql) + `scripts/fetch_intents.py` |
| P4 | Lead-lag : le pic de corrélation croisée se situe à un lag de | [À remplir après rebuild → lag en jours, chart lead-lag] | Idem | [01_active_accounts.sql](queries/01_active_accounts.sql) + chart lot 10 (`charts/leadlag.png`) |
| P5 | Volume Intents vs appels contrats (J−7 → J) | [À remplir après rebuild → `data/merged/daily.csv`, `contract_calls`] | Idem | [03_contract_usage.sql](queries/03_contract_usage.sql) + `scripts/fetch_intents.py` |
| P6 | Volume Intents vs transactions (J−7 → J) | [À remplir après rebuild → `data/merged/daily.csv`, `tx_count`] | Idem | [02_tx_counts.sql](queries/02_tx_counts.sql) + `scripts/fetch_intents.py` |
| P7 | Amélioration vs baseline persistance (RMSE ou R² out-of-sample) | [À remplir après rebuild → métrique + split train/test datés] | Split : train [À remplir → dates], test [À remplir → dates] | `data/merged/daily.csv` + méthode §5 |

Lecture attendue si la thèse tient : P1 > P3 (l'avance J−7 bat le contemporain),
P4 pointe un lag négatif stable (Intents en tête), P7 > 0 (battre la persistance).
Si c'est l'inverse, voir §3 et §5.

Méthode corrélation (sans chiffres inventés) : Pearson sur séries journalières
alignées par `date`, lags J−7/J−14 calculés par décalage calendaire simple ;
p-valeurs et intervalles de confiance à [À remplir après rebuild → méthode bootstrap, n tirages].

## 3. Preuves CONTRE (à remplir après rebuild)

### 3.1 Concentration : l'usage apparent peut venir de quelques acteurs

- Part du top 1 contrat dans les appels `FUNCTION_CALL` : [À remplir après rebuild → `queries/04_top_contracts.sql`].
- Part du top N contrats (N = [À remplir → seuil]) : [À remplir après rebuild → `queries/04_top_contracts.sql`].
- Part des top wallets dans le volume Intents : [À remplir après rebuild → chart lot 11, `charts/concentration.png`].
- Interprétation : si [À remplir → X]% du volume vient de [À remplir → N] wallets,
  la corrélation P1–P3 mesure un comportement de baleines, pas un usage large.
  Sources : [03_contract_usage.sql](queries/03_contract_usage.sql),
  [04_top_contracts.sql](queries/04_top_contracts.sql).

### 3.2 Divergences : jours où Intents et usage réel divergent

- Nombre de jours où le volume Intents monte mais les comptes actifs baissent (et inverse) :
  [À remplir après rebuild → `data/merged/daily.csv`].
- Plus gros écart journalier (résidu standardisé max) le [À remplir → date] :
  [À remplir → valeur].
- Périodes de divergence continue (> [À remplir → X] jours) : [À remplir → dates].
- Interprétation : des divergences fréquentes ou longues affaiblissent le statut
  d'« indicateur avancé » même si la corrélation moyenne est bonne.
  Sources : [01_active_accounts.sql](queries/01_active_accounts.sql),
  [02_tx_counts.sql](queries/02_tx_counts.sql), `scripts/fetch_intents.py`.

### 3.3 Fraîcheur BigQuery (Lake déprécié le 24/03/2026)

- `MAX(block_date)` constaté sur `transactions` au pull du [À remplir → date] :
  [À remplir après rebuild → valeur].
- `MAX(block_date)` constaté sur `receipt_actions` : [À remplir → valeur].
- Retard vs date de pull : [À remplir → N jours].
- Interprétation : si le retard dépasse [À remplir → X] jours, les derniers points
  (les plus informatifs pour un indicateur avancé) manquent et P1–P7 portent sur
  une fenêtre tronquée [À remplir → début → fin réels].
  Sources : [00_sample.sql](queries/00_sample.sql) (requêtes fraîcheur),
  logs `scripts/fetch_bigquery.py` (date de pull, bytes scannés, `MAX(block_date)`).

## 4. Limites

1. **Prix hors sources imposées.** Aucune des sources du dossier
   (`bigquery-public-data.crypto_near_mainnet_us`, Intents Explorer API) ne fournit
   le prix du token. La comparaison « meilleur que le prix » est donc
   **non calculable depuis ces sources**, sauf ajout d'une source prix explicite
   et versionnée : [À remplir → nom + version + URL, ou « non calculable »].
   En l'absence de source prix, la thèse testée se réduit à :
   « le volume Intents avance l'usage réel et bat une baseline persistance ».
2. **Coûts BigQuery.** NEAR paie le stockage, l'exécutant paie les bytes scannés.
   Bytes scannés par requête au pull du [À remplir → date] :
   [À remplir → `01…` : X Go], [À remplir → `02…` : X Go],
   [À remplir → `03…` : X Go], [À remplir → `04…` : X Go].
   Les requêtes ne lisent que les colonnes utiles + partition `block_date`
   (voir en-têtes des SQL). Aucune estimation de coût monétaire n'est donnée ici :
   grille BigQuery en vigueur au moment du rebuild.
3. **Trous et biais Intents.** Couverture API : `GET /transactions` paginé par
   curseur (`lastDepositAddress` + `lastDepositMemo`, `direction=next`,
   `numberOfTransactions` ≤ 1000, 1 req / 5 s). Jours sans données Intents :
   [À remplir après rebuild → dates]. Volume = somme `amountInUsd` des seuls
   `statuses=SUCCESS` ; les statuts non-SUCCESS ([À remplir → part %]) sont exclus,
   ce qui sous-estime l'intention brute. Cache brut : `data/raw/intents_*.json`.
4. **Définition d'« usage réel ».** Comptes actifs = `signer_account_id` distincts
   par `block_date` ([01_active_accounts.sql](queries/01_active_accounts.sql)) :
   un bot multi-comptes compte multiple, un exchange mutualisé compte simple.
   Appels contrats limités à `action_kind = 'FUNCTION_CALL'`
   ([03_contract_usage.sql](queries/03_contract_usage.sql)).
5. **Fenêtre et généralisation.** Résultats valables uniquement sur la fenêtre
   mesurée [À remplir → début → fin réels] ; pas d'extrapolation à d'autres
   périodes ou d'autres chaînes sans nouveau rebuild.

## 5. Seuil d'invalidation (méthode chiffrée, X à remplir après rebuild)

La thèse est **rejetée** si **l'une** des conditions suivantes est vraie
(« OU » logique — un seul échec suffit à changer d'avis) :

- **I1 — Pas d'avance prédictive :** corrélation(J−7 → J) ≤ corrélation(J → J),
  soit P1 ≤ P3 avec les valeurs rebuild. Autrement dit, si
  [À remplir → P1] ≤ [À remplir → P3], le volume Intents ne mène pas.
- **I2 — Lag nul ou inversé :** le pic de corrélation croisée (P4) est à un lag
  de [À remplir → X] jours avec X ≥ 0 (pic contemporain ou Intents en retard).
  Seuil : rejeter si X ≥ 0 ; tenir si X ≤ −[À remplir → seuil en jours] jours.
- **I3 — Ne bat pas la naïveté :** sur le split test daté (§2 P7), le modèle
  « actifs(J) ~ Intents(J−7) » a un RMSE supérieur ou égal à la persistance
  « actifs(J) ~ actifs(J−7) », soit [À remplir → RMSE modèle] ≥ [À remplir → RMSE baseline].
- **I4 — Artefact de concentration :** en retirant les [À remplir → X] plus gros
  wallets Intents (ou le top [À remplir → X] contrats si le retrait wallet est
  impossible), P1 chute de plus de [À remplir → X] points de corrélation
  (de [À remplir → avant] à [À remplir → après]). La thèse « usage large » tombe ;
  il reste au mieux « quelques acteurs avancent ».
- **I5 — Données trop fraîches pour conclure :** retard `MAX(block_date)` >
  [À remplir → X] jours OU fenêtre utile < [À remplir → X] jours
  (n = [À remplir → n]). Verdict : « non testable », pas « validé ».

Formules (variables, aucun seuil numérique imposé avant rebuild) :

- `invalider = (P1 <= P3) OU (lag_pic >= 0) OU (RMSE_modele >= RMSE_persistance)`
  `OU (P1_avant − P1_sans_topX > seuil_concentration) OU (retard > X_jours OU n < X_jours)`
- Chaque X est fixé **avant** lecture des résultats si possible, sinon noté
  « fixé après rebuild » à côté de la valeur — dans ce cas le verdict associé
  est marqué « exploratoire, à confirmer sur nouvelle fenêtre ».

Verdict après rebuild (une ligne, entourer la mention utile) :
**VALIDÉE / REJETÉE / NON TESTABLE** — motif : [À remplir → I1..I5 ou « aucun seuil déclenché »],
date du rebuild : [À remplir → date], commit/données : [À remplir → hash ou identifiant].

## 6. Reproductibilité (checklist jury)

- [ ] `pip install -r requirements.txt` puis `python rebuild.py` : OK le [À remplir → date].
- [ ] Rebuild sans `.env` via `data/raw/` : mêmes chiffres (diff vide le [À remplir → date]).
- [ ] Chaque SQL contient `block_date` : [00_sample.sql](queries/00_sample.sql),
      [01_active_accounts.sql](queries/01_active_accounts.sql),
      [02_tx_counts.sql](queries/02_tx_counts.sql),
      [03_contract_usage.sql](queries/03_contract_usage.sql),
      [04_top_contracts.sql](queries/04_top_contracts.sql).
- [ ] `.env` absent de git ; `.env.example` commité sans secret.
- [ ] `dashboard.html` ouvert Wi-Fi coupé : 5 visuels + requêtes + phrases.
- [ ] Chaque valeur des §2–§5 pointe vers une requête (§2–§3), un log de pull (§3.3, §4.2)
      ou `data/merged/daily.csv` (contrat : `date,active_accounts,tx_count,contract_calls,unique_contracts,intents_swaps,intents_volume_usd`).

## 7. Sources

- [Sujet thèse NEAR (hackathon)](https://raw.githubusercontent.com/nearai/near-hackathon-prompt-examples/main/tracks/02-thesis.md)
- [BigQuery — docs NEAR](https://docs.near.org/data-infrastructure/big-query)
- [Data infrastructure — docs NEAR](https://docs.near.org/data-infrastructure/what-is)
- [Intents Explorer API — introduction](https://docs.near-intents.org/integration/distribution-channels/1click-api/explorer/introduction)
- [Intents Explorer API — transactions](https://docs.near-intents.org/integration/distribution-channels/1click-api/explorer/transactions)
