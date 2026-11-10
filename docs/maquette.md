# NEAR Thesis — Maquette dashboard.html (proposition jury)

> Statut : proposition visuelle pre-lot-12, à discuter avec le parent avant de figer le HTML.
> Contrainte : zéro chiffre inventé. Tous les `[crochets]` sont remplis par `build_dashboard.py` depuis `daily.csv` + logs.

## 1. Intention jury (30 secondes)

Le jury doit comprendre sans scroller : le claim, le verdict (nuancé), et que tout est reproductible en 1 commande.
Le reste de la page = preuve ordonnée + contre-preuve honnête + méthode vérifiable.

Lecture cible : claim → courbe reine → test lead-lag → contexte → contre-preuve → méthode → verdict.

## 2. Ordre recommandé des 5 blocs

| # | Bloc | Lot source | Rôle jury |
|---|------|-----------|-----------|
| 1 | Actifs quotidiens vs volume Intents (double axe) | 08 | Preuve principale : les deux courbes bougent-elles ensemble ? |
| 2 | Lead-lag : Intents J-7 / J-14 vs actifs J | 10 | Cœur du claim « avancé » : le volume précède-t-il l'usage ? |
| 3 | Transactions + contrats uniques | 09 | Contexte « usage réel » : l'activité n'est pas qu'un compteur |
| 4 | Concentration : top wallets + part du volume | 11 | Contre-preuve assumée : si N wallets = P % du volume, le signal est fragile |
| 5 | Fraîcheur + coût + reproductibilité | 01/05/07 | Confiance : MAX(block_date), bytes scannés, date de pull, fenêtre |

Pourquoi cet ordre : on donne d'abord la meilleure preuve (1), puis le test discriminant du mot « avancé » (2), puis le contexte qui élargit (3), puis on attaque soi-même le claim (4), puis on prouve le sérieux (5). Le jury pardonne un claim nuancé, jamais une contre-preuve cachée.

Variante écartée : mettre la concentration en 2. Trop défensif ; le jury n'a pas encore vu la preuve à attaquer.

## 3. Wireframe textuel de la page

```
┌─ HEADER (sticky non, simple bandeau) ─────────────────────┐
│ Titre : NEAR Intents, indicateur avancé de l'usage réel ?  │
│ Claim 1 ligne + badge verdict : [CONFIRMÉ / NUANCÉ /       │
│ INFIRMÉ] + fenêtre [2026-10-01 → MAX(block_date)]          │
│ Meta : pull du [date], MAX(block_date)=[date], prix :      │
│ [source versionnée | non calculable depuis ces sources]    │
│ Sommaire ancré : 1 Preuve · 2 Lead-lag · 3 Contexte ·      │
│ 4 Limites · 5 Méthode                                      │
├─ BLOC 0 : VERDICT (3 lignes, pas de chart) ───────────────┤
│ « Sur [fenêtre], [1 phrase verdict]. Seuil qui ferait      │
│ changer d'avis : [seuil THESIS.md]. »                      │
│ Lien : rebuild.py · THESIS.md · daily.csv                  │
├─ BLOC 1 : PREUVE PRINCIPALE ──────────────────────────────┤
│ H2 « 1. Actifs quotidiens vs volume Intents »              │
│ [chart-01 PNG base64, ~900px, légende axes]                │
│ ▶ Phrase factuelle #1 (gras, 1 ligne)                      │
│ ▶ <details>Requête exacte</details> : 01_active_accounts   │
│   + agrégation intents (+ lien queries/*.sql)              │
│ ▶ Lecture jury : 1 ligne « ce que ça montre / ne montre   │
│   pas »                                                    │
├─ BLOC 2 : TEST LEAD-LAG ──────────────────────────────────┤
│ H2 « 2. Le volume précède-t-il l'usage ? (J-7, J-14) »     │
│ [chart-03 PNG]                                             │
│ ▶ Phrase factuelle #2                                      │
│ ▶ <details>Requête + méthode de décalage</details>         │
│ ▶ Lecture jury : 1 ligne                                   │
├─ BLOC 3 : CONTEXTE USAGE ─────────────────────────────────┤
│ H2 « 3. Transactions et contrats : l'usage derrière »      │
│ [chart-02 PNG]                                             │
│ ▶ Phrase factuelle #3                                      │
│ ▶ <details>Requêtes</details> : 02_tx_counts +             │
│   03_contract_usage (+ top contrats)                       │
│ ▶ Lecture jury : 1 ligne                                   │
├─ BLOC 4 : CONTRE-PREUVE (fond distinct, voir palette) ────┤
│ H2 « 4. Limites : concentration du volume »                │
│ [chart-04 PNG : top wallets + part cumulée]                │
│ ▶ Phrase factuelle #4 (formulée en risque, pas en excuse)  │
│ ▶ <details>Requête + périmètre</details>                   │
│ ▶ « Ce que ça change au claim » : 1-2 lignes honnêtes      │
├─ BLOC 5 : MÉTHODE / REPRODUCTIBILITÉ ─────────────────────┤
│ H2 « 5. Méthode et fraîcheur des données »                 │
│ Pas de chart, tableau 4 lignes : MAX(block_date) · date    │
│ de pull · bytes BigQuery scannés · fenêtre + note Lake     │
│ (déprécié 24/03/2026)                                      │
│ ▶ Phrase factuelle #5 (fraîcheur, pas un résultat)         │
│ ▶ <details>Sample query 00 + contrat daily.csv</details>   │
│ ▶ Commande : pip install -r requirements.txt &&            │
│   python rebuild.py (rebuild sans .env via data/raw/)      │
├─ FOOTER ──────────────────────────────────────────────────┤
│ Claim rappelé 1 ligne · verdict · seuil d'infirmation      │
│ Sources : 5 liens (hackathon, BigQuery x2, explorer x2)    │
│ « Chaque chiffre pointe vers une requête ou un log.        │
│ JWT jamais commité (.env.example seul). »                   │
└───────────────────────────────────────────────────────────┘
```

Règles communes à chaque bloc 1-4 : `1 chart = 1 <details>requête exacte</details> = 1 phrase factuelle = 1 ligne de lecture`. Le bloc 5 remplace le chart par le tableau de fraîcheur (c'est le 5e « visuel » attendu hors-ligne).

## 4. Gabarits des 5 phrases factuelles (SANS chiffres inventés)

À remplir par le lot 12 depuis les données réelles. Ne jamais reformuler en causalité.

1. (Bloc 1) « Du `[date_min]` au `[date_max]` (`[N]` jours), la moyenne quotidienne des comptes actifs est de `[X]` et le volume Intents SUCCESS moyen de `[Y]` USD/jour ; les deux séries `[montent/baissent/divergent — décrire, pas expliquer]`. »
2. (Bloc 2) « Le volume Intents décalé de `[7/14]` jours obtient une corrélation de `[r]` avec les actifs du jour J, contre `[r0]` sans décalage, sur `[N]` jours. »
3. (Bloc 3) « Sur la fenêtre, `[T]` transactions/jour en moyenne et `[C]` contrats uniques/jour ; le top `[K]` contrats concentre `[P]` % des appels. »
4. (Bloc 4, contre-preuve) « Le top `[K]` wallets représente `[P]` % du volume Intents SUCCESS sur la fenêtre : le signal repose donc sur `[peu/beaucoup]` d'acteurs. »
5. (Bloc 5, fraîcheur) « Données BigQuery au `MAX(block_date)=[date]` (pull du `[date]`, `[B]` bytes scannés) ; fenêtre `[date_min → date_max]` ; prix `[source + version | non calculable depuis ces sources]`. »

Interdits : « prouve que », « grâce à », tout % ou r inventé, toute date hors logs.

## 5. Palette et structure CSS inline

Contraintes lot 12 : un seul fichier, CSS inline dans `<style>`, images en base64, zéro requête réseau, lisible Wi-Fi coupé, police système.

Palette recommandée (sobre, accessible, imprimable) :
- Fond page : `#FAFAF7` ; cartes : `#FFFFFF` ; bordures : `#E3E0D8`
- Texte : `#1A1A18` ; secondaire : `#5C5A55`
- Accent preuve (titres H2, liens) : `#0B4F3A` (vert académique)
- Accent contre-preuve (bloc 4 uniquement) : fond `#FFF4E8`, bordure `#C77B2E`, titre `#8A4A00`
- Verdict : pastille `[CONFIRMÉ #0B4F3A | NUANCÉ #8A4A00 | INFIRMÉ #8B1E1E]` sur fond clair
- Code/requêtes : fond `#F1EFEA`, police `ui-monospace, monospace`, taille `0.85em`

Structure CSS (classes minimales, ~80 lignes) :

```html
<style>
  :root { --bg:#FAFAF7; --card:#FFF; --ink:#1A1A18; --muted:#5C5A55;
          --line:#E3E0D8; --accent:#0B4F3A; --warn-bg:#FFF4E8;
          --warn-line:#C77B2E; --warn-ink:#8A4A00; --code:#F1EFEA; }
  body { background:var(--bg); color:var(--ink);
         font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
         max-width:960px; margin:0 auto; padding:24px; line-height:1.55; }
  header, section.card, footer { background:var(--card);
    border:1px solid var(--line); border-radius:10px; padding:20px 24px;
    margin-bottom:20px; }
  section.warn { background:var(--warn-bg); border-color:var(--warn-line); }
  section.warn h2 { color:var(--warn-ink); }
  h2 { color:var(--accent); font-size:1.15rem; margin-top:0; }
  img.chart { width:100%; height:auto; border:1px solid var(--line);
    border-radius:6px; background:#fff; }
  p.fact { font-weight:600; }
  p.reading { color:var(--muted); font-size:.95em; }
  details { margin-top:12px; } summary { cursor:pointer; color:var(--accent); }
  pre { background:var(--code); padding:12px; overflow-x:auto;
    border-radius:6px; font-size:.85em; }
  table.fresh { border-collapse:collapse; width:100%; font-size:.92em; }
  table.fresh td, table.fresh th { border:1px solid var(--line); padding:6px 10px; }
  .badge { display:inline-block; padding:2px 10px; border-radius:999px;
    font-weight:700; font-size:.85em; }
  nav.toc a { color:var(--accent); margin-right:12px; font-size:.9em; }
  @media print { body { background:#fff; } section.warn { -webkit-print-color-adjust:exact; } }
</style>
```

Structure HTML : `header` (titre+claim+badge+toc) → `section.verdict` → `section.card` x3 (blocs 1-3) → `section.card.warn` (bloc 4) → `section.card` (bloc 5, tableau `.fresh`) → `footer`. Chaque chart : `<img class="chart" src="data:image/png;base64,..." alt="...">`.

## 6. Deux options contrastées

### Option A — Sobre académique (recommandée)

- Page linéaire, 5 sections numérotées, verdict en haut, contre-preuve banalisée dans le flux (bloc 4 sur fond légèrement distinct).
- Phrases factuelles sèches (gabarits §4), zéro storytelling, requêtes repliées par défaut.
- Avantages : crédibilité maximale, lecture jury rapide, print propre, zéro risque de « marketing ».
- Inconvénients : moins mémorable si le jury lit 20 dossiers.

### Option B — Narratif « enquête »

- Même 5 blocs mais titrés en questions (« Le volume annonce-t-il l'usage ? », « Qui pèse vraiment ? »), fil conducteur verdict→suspense→révélation, bloc 4 mis en scène (« L'objection qui pourrait tout changer »).
- Phrases factuelles identiques mais précédées d'une accroche narrative.
- Avantages : mémorable, guide un jury non-technique.
- Inconvénients : risque de paraître orienté ; chaque ligne narrative est une ligne attaquable ; plus long à lire.

## 7. Recommandation

**Option A, sobre académique**, avec un seul emprunt à B : titrer chaque bloc en question factuelle courte suivie du sujet (ex. « 2. Le volume précède-t-il l'usage ? — test J-7/J-14 »). Le jury d'une thèse-note récompense la reproductibilité et l'honnêteté de la contre-preuve, pas le récit. La mémorabilité viendra du badge verdict + seuil d'infirmation affichés dès le header, pas d'effets.

Points à figer avec le lot 12 : ordre §2 inchangé ; gabarits §4 remplis par script (jamais à la main) ; palette §5 telle quelle ; `<details>` fermés par défaut sauf le verdict.

## 8. Trois questions ouvertes pour le parent

1. Verdict affiché dès le header (recommandé : transparent mais engageant) ou verdict repoussé en footer après les preuves (suspense, mais jury pressé) ?
2. Bloc 4 contre-preuve : le garder en position 4 dans le flux (honnête, fluide) ou l'extraire en bandeau pleine largeur plus visible (signal fort d'honnêteté, mais casse la grille) ?
3. 5e visuel : valides-tu le tableau fraîcheur/coût comme 5e « visuel » (utile au jury, pas de PNG), ou exiges-tu un 5e PNG (ex. courbe volume brut) quitte à ajouter un lot chart ?

## 9. Décisions figées (parent + design-advisor)

- **Q1 — Verdict en header : TRANCHÉ (parent).** Badge verdict + claim + fenêtre dès le header, verdict détaillé en bloc 0. Transparent, wireframe §3 inchangé.
- **Q2 — Contre-preuve dans le flux : TRANCHÉ (design-advisor).** Bloc 4 en position 4, `section.card.warn` (fond `#FFF4E8`), pas de bandeau pleine largeur : l'honnêteté banalisée vaut plus qu'exhibée, et la grille reste linéaire (option A).
- **Q3 — 5e visuel = tableau fraîcheur : TRANCHÉ (design-advisor).** Pas de 5e PNG : le tableau MAX/pull/bytes/fenêtre sert la note jury (reproductibilité), un volume brut ferait doublon avec le bloc 1.

## 10. Checklist exhaustive des éléments du visuel (51)

Le lot 12 a livré sur cette base ; cette checklist sert à la vérification et à l'ajustement final de `dashboard.html`. Aucun `[crochet]` rempli à la main : que `daily.csv` + logs.

### Header (8)
- [ ] 1. Titre : « NEAR Intents, indicateur avancé de l'usage réel ? »
- [ ] 2. Claim en 1 ligne (reprise exacte de THESIS.md)
- [ ] 3. Badge verdict `[CONFIRMÉ / NUANCÉ / INFIRMÉ]` (pastille couleur §5)
- [ ] 4. Fenêtre `[date_min → MAX(block_date)]`
- [ ] 5. Meta : date de pull `[date]`
- [ ] 6. Meta : `MAX(block_date)=[date]`
- [ ] 7. Meta prix : `[source + version | non calculable depuis ces sources]`
- [ ] 8. Sommaire ancré : 5 liens (1 Preuve · 2 Lead-lag · 3 Contexte · 4 Limites · 5 Méthode)

### Bloc 0 — Verdict (5)
- [ ] 9. Phrase verdict (3 lignes max, gabarit §4/intro)
- [ ] 10. Seuil qui ferait changer d'avis (reprise THESIS.md)
- [ ] 11. Lien `rebuild.py`
- [ ] 12. Lien `THESIS.md`
- [ ] 13. Lien `data/merged/daily.csv`

### Bloc 1 — Preuve principale (5)
- [ ] 14. Titre H2 « 1. Actifs quotidiens vs volume Intents »
- [ ] 15. Chart-01 PNG base64 double axe + attribut `alt` descriptif
- [ ] 16. Phrase factuelle #1 (gabarit §4, gras)
- [ ] 17. `<details>` requête exacte : `01_active_accounts` + agrégation intents
- [ ] 18. Ligne « lecture jury » (montre / ne montre pas)

### Bloc 2 — Lead-lag (5)
- [ ] 19. Titre H2 « 2. Le volume précède-t-il l'usage ? — test J-7/J-14 »
- [ ] 20. Chart PNG base64 lead-lag + `alt`
- [ ] 21. Phrase factuelle #2 (gabarit §4, gras)
- [ ] 22. `<details>` requête + méthode de décalage
- [ ] 23. Ligne « lecture jury »

### Bloc 3 — Contexte usage (5)
- [ ] 24. Titre H2 « 3. Transactions et contrats : l'usage derrière »
- [ ] 25. Charts PNG base64 tx + contrats + `alt`
- [ ] 26. Phrase factuelle #3 (gabarit §4, gras)
- [ ] 27. `<details>` requêtes : `02_tx_counts` + `03_contract_usage` (+ top contrats)
- [ ] 28. Ligne « lecture jury »

### Bloc 4 — Contre-preuve (5)
- [ ] 29. Titre H2 « 4. Limites : concentration du volume » (style warn §5)
- [ ] 30. Chart PNG base64 (top wallets + part cumulée) + `alt`
- [ ] 31. Phrase factuelle #4 formulée en risque (gabarit §4, gras)
- [ ] 32. `<details>` requête + périmètre
- [ ] 33. Ligne « ce que ça change au claim » (1-2 lignes honnêtes)

### Bloc 5 — Méthode / fraîcheur (8)
- [ ] 34. Titre H2 « 5. Méthode et fraîcheur des données »
- [ ] 35. Tableau : ligne `MAX(block_date)=[date]`
- [ ] 36. Tableau : ligne date de pull `[date]`
- [ ] 37. Tableau : ligne bytes BigQuery scannés `[B]`
- [ ] 38. Tableau : ligne fenêtre `[date_min → date_max]` + note Lake (déprécié 24/03/2026)
- [ ] 39. Phrase factuelle #5 fraîcheur (gabarit §4)
- [ ] 40. `<details>` sample query `00` + contrat `daily.csv`
- [ ] 41. Commande `pip install -r requirements.txt && python rebuild.py` (+ note rebuild sans `.env` via `data/raw/`)

### Footer (10)
- [ ] 42. Claim rappelé en 1 ligne
- [ ] 43. Verdict rappelé (cohérent avec le badge header)
- [ ] 44. Seuil d'infirmation rappelé
- [ ] 45. Lien source : prompt hackathon (`02-thesis.md`)
- [ ] 46. Lien source : docs BigQuery (`big-query`)
- [ ] 47. Lien source : docs (`what-is`)
- [ ] 48. Lien source : explorer (`introduction`)
- [ ] 49. Lien source : explorer (`transactions`)
- [ ] 50. Note « JWT jamais commité (`.env.example` seul) »
- [ ] 51. Note « Chaque chiffre pointe vers une requête ou un log »
