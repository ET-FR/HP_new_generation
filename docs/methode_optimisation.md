# Méthode d'optimisation des formes d'échange : décision

Décidé le 9 novembre 2026, après une recherche bibliographique sur les algorithmes adaptés
à une CFD coûteuse (minutes à heures par cas), 10 à 20 variables, plusieurs objectifs,
des contraintes et des variables mixtes (continues et choix discrets).

## Méthode principale retenue

**Optimisation bayésienne multi-objectif avec contraintes (qNEHVI), multi-fidélité, par lots parallèles.**

- Outil : **Ax** (Meta) construit sur **BoTorch** (Python, libre). Gère variables mixtes,
  multi-objectif, contraintes, multi-fidélité.
- Fidélités : modèle analytique (`pac_fenetre/`, fraction de seconde) → CFD 2D périodique
  grossière (OpenFOAM, ~1 min) → CFD fine ou 3D.
- Objectif cible : performance saisonnière de la machine dans les deux modes (chauffage 7 °C
  et -7 °C avec givre, clim 35 °C), calculée par le simulateur ; contrainte charge R290 ≤ 152 g
  et encombrement de fenêtre.
- Budget visé : quelques centaines de simulations CFD au total (contre 5 000 chez Tancabel 2020).

## Méthodes de secours

| Cas | Méthode |
|---|---|
| Plus de ~20 variables | TuRBO (régions de confiance) ou SAASBO (sélection des variables), dans BoTorch |
| Beaucoup de processeurs en parallèle et simulations courtes | SAEA (krigeage + NSGA-II), à comparer sur nos cas |
| Affinage final d'une forme choisie (centaines de variables) | Optimisation adjointe OpenFOAM (`adjointOptimisationFoam`) |
| Plus tard, avec une grosse base de simulations | IA générative (modèles de diffusion guidés, ex. HeatGen, arXiv 2511.09578) |

## Écartées comme méthode principale

- GA / NSGA-II / PSO directement sur la CFD : 10^4 à 10^5 évaluations (ex. 210 810 simulations
  OpenFOAM pour une étude d'ailettes ; > 140 000 CFD pour un faisceau de tubes).
- CMA-ES : robuste mais des milliers d'évaluations ; seulement sur modèle rapide.
- IA générative : pas de base d'entraînement, aucune application air / réfrigérant publiée.

## Éléments de preuve (résumés lus, pas les articles complets)

- Pas d'étude comparant directement ces méthodes sur un échangeur à budget CFD égal.
- Optimisation bayésienne meilleure jusqu'à ~20 variables continues (benchmark Applied Soft
  Computing 2023, S1568494623007627).
- Multi-fidélité bayésienne sur un brûleur en CFD : -57 % de temps de calcul ; 313 → 122 h CPU
  en multi-objectif (arXiv 2511.23140).
- Multi-objectif bayésien vs NSGA-II (autres domaines) : 100 à 200 évaluations contre des milliers.

## Prochaine étape

Brancher Ax / BoTorch sur `pac_fenetre/tpms.py` et le simulateur, d'abord avec le modèle
analytique seul pour valider la boucle, puis ajouter la CFD OpenFOAM comme fidélité haute.
