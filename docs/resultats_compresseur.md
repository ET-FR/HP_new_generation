# Étude du compresseur (résultats générés)

Généré par `python outils/etude_compresseur.py`. Compresseur générique du simulateur, puissance fixée par la régulation.

## 1. État actuel aux points de référence

« COP perdu par le compresseur » : écart entre le cycle réel avec compression isentropique et le COP après compression et moteur (cascade de pertes du simulateur).

| Point | f (tr/s) | Te / Tc (°C) | PR | η_v | η_is | η_mot | η global | COP perdu par le compresseur | COP unité |
|---|---|---|---|---|---|---|---|---|---|
| Chauffage 7/20, 1,6 kW | 28 | 2.9 / 34.3 | 2.41 | 0.92 | 0.70 | 0.91 | 0.62 | 35 % | 4.93 |
| Chauffage 7/20, 3,2 kW | 60 | 1.8 / 40.1 | 2.86 | 0.91 | 0.72 | 0.93 | 0.65 | 32 % | 4.15 |
| Chauffage 2/20, 2,5 kW | 53 | -2.8 / 36.7 | 3.05 | 0.90 | 0.72 | 0.93 | 0.65 | 32 % | 3.99 |
| Clim 35/27, 1,5 kW sens. | 24 | 12.6 / 42.7 | 2.21 | 0.93 | 0.70 | 0.91 | 0.61 | 39 % | 4.45 |
| Clim 35/27, 2,6 kW sens. | 52 | 9.6 / 45.8 | 2.59 | 0.92 | 0.72 | 0.93 | 0.65 | 35 % | 3.70 |

## 2. η global requis pour un COP cible

η global = η_is · η_mot · η_var. Cycle figé (approximation). « améliorés » : UA x2, débits d'air x1,5 (voir README).

| Point | Échangeurs | η global actuel | COP actuel | η requis COP 5 | η requis COP 5.5 | η requis COP 6 |
|---|---|---|---|---|---|---|
| Chauffage 7/20, 1,6 kW | actuels | 0.62 | 4.93 | 0.63 | 0.70 | 0.77 |
| Chauffage 7/20, 3,2 kW | actuels | 0.65 | 4.15 | 0.80 | 0.89 | 0.99 |
| Chauffage 2/20, 2,5 kW | actuels | 0.65 | 3.99 | 0.84 | 0.93 | 1.03 |
| Clim 35/27, 1,5 kW sens. | actuels | 0.61 | 4.45 | 0.70 | 0.77 | 0.85 |
| Clim 35/27, 2,6 kW sens. | actuels | 0.65 | 3.70 | 0.90 | 1.00 | 1.11 |
| Chauffage 7/20, 1,6 kW | améliorés | 0.62 | 5.75 | 0.53 | 0.59 | 0.65 |
| Chauffage 7/20, 3,2 kW | améliorés | 0.65 | 5.02 | 0.64 | 0.72 | 0.80 |
| Chauffage 2/20, 2,5 kW | améliorés | 0.65 | 4.61 | 0.71 | 0.80 | 0.88 |
| Clim 35/27, 1,5 kW sens. | améliorés | 0.60 | 5.83 | 0.51 | 0.56 | 0.62 |
| Clim 35/27, 2,6 kW sens. | améliorés | 0.63 | 4.93 | 0.64 | 0.72 | 0.79 |

## 3. Sensibilité au rendement isentropique maximal

COP unité (fréquence en tr/s entre parenthèses).

| eta_is_max | Chauffage 7/20, 1,6 kW | Chauffage 7/20, 3,2 kW | Chauffage 2/20, 2,5 kW | Clim 35/27, 1,5 kW sens. | Clim 35/27, 2,6 kW sens. |
|---|---|---|---|---|---|
| 0.65 | 4.55 (28) | 3.84 (59) | 3.70 (52) | 4.02 (25) | 3.35 (52) |
| 0.70 | 4.82 (28) | 4.06 (60) | 3.90 (53) | 4.32 (24) | 3.60 (52) |
| 0.72 | 4.93 (28) | 4.15 (60) | 3.99 (53) | 4.45 (24) | 3.70 (52) |
| 0.75 | 5.09 (28) | 4.28 (61) | 4.11 (54) | 4.63 (24) | 3.85 (52) |
| 0.78 | 5.26 (28) | 4.41 (61) | 4.23 (54) | 4.80 (24) | 4.00 (52) |
| 0.82 | 5.46 (29) | 4.49 (61) | 4.31 (54) | 5.04 (24) | 4.11 (52) |

## 4. Sensibilité au rendement moteur maximal

| eta_mot_max | Chauffage 7/20, 1,6 kW | Chauffage 7/20, 3,2 kW | Chauffage 2/20, 2,5 kW | Clim 35/27, 1,5 kW sens. | Clim 35/27, 2,6 kW sens. |
|---|---|---|---|---|---|
| 0.900 | 4.76 (28) | 4.01 (60) | 3.85 (53) | 4.28 (24) | 3.57 (52) |
| 0.935 | 4.93 (28) | 4.15 (60) | 3.99 (53) | 4.45 (24) | 3.70 (52) |
| 0.950 | 5.01 (28) | 4.21 (60) | 4.04 (53) | 4.51 (24) | 3.76 (52) |
| 0.965 | 5.08 (28) | 4.27 (60) | 4.10 (53) | 4.58 (24) | 3.81 (52) |

## 5. Cylindrée

Le modèle générique garde le meilleur rendement à 55 tr/s (η_is) et 70 tr/s (moteur) quelle que soit la cylindrée : la tendance dépend de cette hypothèse, à confirmer sur des cartes réelles.

Ventilateurs asservis à la fréquence (régulation actuelle du simulateur) :

| cylindree_cm3 | Chauffage 7/20, 1,6 kW | Chauffage 7/20, 3,2 kW | Chauffage 2/20, 2,5 kW | Clim 35/27, 1,5 kW sens. | Clim 35/27, 2,6 kW sens. |
|---|---|---|---|---|---|
| 10 | 5.18 (43) | 4.11 (92) | 3.92 (81) | 4.93 (36) | 4.00 (70) |
| 12 | 5.11 (37) | 4.20 (77) | 4.01 (69) | 4.75 (31) | 3.91 (61) |
| 14 | 5.02 (32) | 4.20 (68) | 4.02 (60) | 4.59 (27) | 3.81 (56) |
| 16 | 4.93 (28) | 4.15 (60) | 3.99 (53) | 4.45 (24) | 3.70 (52) |
| 20 | 4.76 (23) | 4.00 (50) | 3.87 (44) | 4.22 (20) | 3.50 (46) |
| 24 | 4.63 (19) | 3.84 (42) | 3.74 (37) | 4.04 (18) | 3.31 (41) |

Ventilateurs à débit nominal fixe (effet du compresseur seul) :

| cylindree_cm3 | Chauffage 7/20, 1,6 kW | Chauffage 7/20, 3,2 kW | Chauffage 2/20, 2,5 kW | Clim 35/27, 1,5 kW sens. | Clim 35/27, 2,6 kW sens. |
|---|---|---|---|---|---|
| 10 | 5.02 (43) | 4.00 (95) | 3.96 (83) | 5.04 (32) | 3.85 (75) |
| 12 | 4.98 (36) | 4.10 (80) | 4.01 (70) | 4.99 (27) | 3.88 (63) |
| 14 | 4.94 (31) | 4.14 (69) | 4.02 (60) | 4.95 (23) | 3.88 (54) |
| 16 | 4.91 (27) | 4.15 (60) | 4.01 (53) | 4.92 (20) | 3.86 (47) |
| 20 | 4.85 (21) | 4.13 (48) | 3.98 (42) | 4.86 (16) | 3.81 (38) |
| 24 | 4.81 (18) | 4.09 (40) | 3.94 (35) | hors plage | 3.77 (32) |

Plage de modulation (f_min = 15 tr/s, f_max = 110 tr/s) :

| Cylindrée (cm³) | P mini à 7 °C, f_min (kW) | P maxi à -7 °C, f_max (kW) |
|---|---|---|
| 10 | 0.59 | 2.58 |
| 12 | 0.69 | 2.99 |
| 14 | 0.80 | 3.39 |
| 16 | 0.90 | 3.77 |
| 20 | 1.09 | 4.48 |
| 24 | 1.28 | 5.14 |
