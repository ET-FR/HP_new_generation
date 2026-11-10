# Méthode d'optimisation des formes d'échange : décision

Décidé le 9 novembre 2026, après une recherche bibliographique sur les algorithmes adaptés
à une CFD coûteuse (minutes à heures par cas), 10 à 20 variables, plusieurs objectifs,
des contraintes et des variables mixtes (continues et choix discrets).

## Méthode principale retenue

**Optimisation bayésienne multi-objectif avec contraintes (qNEHVI), multi-fidélité, par lots parallèles.**

- Outil : **Ax** (Meta) construit sur **BoTorch** (Python, libre). Gère variables mixtes,
  multi-objectif, contraintes, multi-fidélité.
- Fidélités : modèle analytique (`pac_fenetre/`, fraction de seconde) → CFD d'une cellule
  périodique (OpenFOAM, ~7 min sur 4 cœurs, mesuré ci-dessous) → CFD fine ou batterie 3D.
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

## Étape 1 : base initiale de simulations

Décidé le 9 novembre 2026 : avant l'optimisation bayésienne, constituer une base tirée au
hasard (hypercube latin). Elle sert de fidélité « moyenne » pour la multi-fidélité, à recaler
le modèle analytique, à comprendre l'influence de chaque paramètre, et de premier noyau pour
un futur modèle génératif.

### Coût mesuré d'un cas (9 novembre 2026)

Cas `outils/cfd_tpms` : gyroïde, Dh 4 mm, porosité 0,6, profondeur 24 mm, Re 200 (laminaire),
finesse 8, raffinement 2, 3 000 itérations. Conteneur cloud 4 cœurs, OpenFOAM v1912 (Ubuntu).

| Étape | Durée |
|---|---|
| blockMesh + snappyHexMesh (136 000 cellules) | 55 s |
| simpleFoam, 4 cœurs, 3 000 itérations (0,12 s / itération) | 6 min 14 s |
| **Total par cas** | **≈ 7,5 min** |

Coupe du maillage : `docs/formes/tpms_gyroide/maillage.png`. Réserves : fonctions de mesure retirées
(défaut de la v1912 Ubuntu, pas du code) ; durée à recontrôler en v2412 ; les cas turbulents
(k-ω SST, Re > 300) coûteront environ 30 % de plus (deux équations de plus).

Ordres de grandeur pour 400 cas : ≈ 50 h sur 4 cœurs ; ≈ 25 h sur 8 cœurs (2 cas × 4 cœurs) ;
≈ 3 à 4 h sur une machine cloud de 64 cœurs.

### Contenu proposé (à valider)

| Variable | Plage |
|---|---|
| Surface | gyroïde, Diamond, FKS, I-WP, Primitive |
| Porosité côté air | 0,5 à 0,8 |
| Dh air | 2 à 6 mm |
| Profondeur du noyau | 12 à 36 mm |
| Re | 100 à 1 600 |

Environ 300 à 500 cas, tirés par hypercube latin dans chaque famille de surface.
Sorties : j, f, h, Δp, plus la fluctuation (écoulement oscillant au-delà de Re ≈ 150).

### Vérifications avant de lancer la base

1. Convergence en maillage (finesse, raffinement) à Re bas et haut.
2. Couches limites (`addLayers`, aujourd'hui désactivé) pour les cas k-ω SST à Re élevé.
3. Résidus : ils plafonnent vers 4e-3 (écoulement oscillant, valeurs moyennées sur le dernier
   quart). Tester si 1 000 à 1 500 itérations donnent les mêmes j et f : jusqu'à 2 à 3 fois
   moins de calcul.
4. Format de stockage réutilisable (paramètres + résultats + métadonnées de maillage), pour
   l'optimisation bayésienne puis un éventuel modèle génératif.

## Prochaine étape

Brancher Ax / BoTorch sur `pac_fenetre/tpms.py` et le simulateur, d'abord avec le modèle
analytique seul pour valider la boucle, puis ajouter la CFD OpenFOAM comme fidélité haute.
