# AGENTS.md — règles générales pour tous les agents (CI, code, voix)

Recopié depuis `Downloads/agents.md` (règle du fichier source : ces règles
doivent figurer dans chaque nouveau dépôt). Exception sécurité : la section 4
a été expurgée des valeurs de clés — voir note ci-dessous.

## 1. CI — jamais plus de 5 minutes

- Toute la CI d'un projet (lint, tests, build) doit se terminer en **moins de 5 minutes** au total.
- À la création de tout nouveau dépôt, configurer la CI pour respecter cette limite :
  - parallaxer les tests et le lint (matrice de jobs) au lieu de les séquentiels ;
  - activer le cache des dépendances (npm/pnpm/yarn cache, pip cache, Cargo cache, etc.) ;
  - ne lancer que les tests impactés par le diff quand c'est possible (turborepo, nx, pytest --selected, etc.) ;
  - limiter les suites à ce qui est nécessaire sur chaque PR (les tests lourds/intégration seulement sur tag, nightly ou demandé) ;
  - activer le mode CI de l'outil de build (vitest --run, jest --ci, etc.) et_timeout courts avec fail-fast.
- Si une CI dépasse 5 minutes, c'est un bug à corriger : déplier, réduire la granularité des jobs, cacher, isoler les tests lents — pas juste augmenter le timeout.

## 2. Taille du code

- **Fichiers de code : jamais plus de 500 lignes.** Au-delà, découper en modules séparés (un module = une responsabilité).
- **Fonctions : jamais plus de 50 lignes.** Au-delà, extraire des sous-fonctions avec un nom explicite.

## 3. Réutilisabilité maximale du code

- Écrire le code le plus réutilisable possible :
  - pas de logique dupliquée — si un même bloc existe à deux endroits, l'extraire dans une fonction ou un module partagé ;
  - séparer la logique métier (testable, pure) de l'interface / du système de fichiers / du réseau ;
  - glanages config-driven : constantes en haut de fichier ou dans un fichier de config, pas en dur au milieu du code ;
  - noms, conventions typiques du langage utilisé, petits fichiers, petits exports, API claires — tout doit être importable ailleurs sans effet de bord ;
  - privilégier la composition : petites fonctions combinées plutôt que gros blocs monolithiques.

## 4. Voix avec ElevenLabs (clés expurgées — ne jamais les remettre ici)

Quand une tâche nécessite de la synthèse vocale (TTS) avec ElevenLabs,
utiliser l'une des deux clés `XI_API_KEY` (comptes gaia et Baptiste),
conservées HORS des dépôts (gestionnaire de secrets / `.env` local git-ignoré).

- Mettre la clé dans une variable d'environnement (`.env`, secret CI), **jamais en dur dans le code source commité, et jamais dans ce fichier**.
- En cas d'échec (quota, erreur d'API) sur une clé, tenter l'autre clé.
- NOTE : la source `Downloads/agents.md` contient actuellement les valeurs en clair
  (risque de propagation via cette règle de recopie). Ne pas recopier les valeurs.
  Recommandé : les retirer de la source et les déplacer vers un gestionnaire de secrets.
