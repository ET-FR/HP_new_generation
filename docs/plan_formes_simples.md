# Plan d'étude : formes simples côté air

Établi le 9 novembre 2026. Objectif : comprendre l'effet de la géométrie sur l'écoulement
d'air et sur l'échange, et valider la chaîne CFD, **avant** l'optimisation bayésienne
(`docs/methode_optimisation.md`). Aucune simulation lancée tant que ce plan n'est pas validé.

## 1. Décisions prises

| Sujet | Décision |
|---|---|
| Critère d'équité entre formes | **Même charge de propane** et **même périmètre de contact air / propane**, par unité de surface frontale |
| Vitesse frontale de l'air | **1 m/s** pour toutes les comparaisons |
| Ailettes | **Plus tard**, après les tubes |

## 2. Conséquence géométrique du critère d'équité

Pour un tube seul, on ne peut pas avoir à la fois la même section et le même périmètre
qu'un tube rond : à section égale, le cercle est la forme de plus petit périmètre
(inégalité isopérimétrique). Le critère s'applique donc **à l'ensemble de la batterie**,
par unité de surface frontale :

- section intérieure totale égale → même volume de propane, donc même charge ;
- périmètre intérieur total égal → même surface de contact air / propane.

Les deux ensemble imposent le **même diamètre hydraulique intérieur** Dh = 4 A / P pour
toutes les formes. Chaque forme a alors sa propre taille, et le **nombre de tubes** s'ajuste
pour garder la même section totale : N / N_rond = A_rond / A_forme.

Avec Dh = 4 mm, A (mm²) = P (mm) pour toutes les formes :

| Forme (canal intérieur) | Dimensions | A (mm²) = P (mm) | Tubes relatifs N / N_rond |
|---|---|---|---|
| Rond (référence) | Ø 4 mm | 12,57 | 1,00 |
| Carré, et carré à 45° (losange) | 4 × 4 mm | 16,00 | 0,79 |
| Triangle équilatéral (2 orientations) | côté 6,93 mm | 20,78 | 0,61 |
| Ellipse 2:1 (grand axe dans le sens de l'air) | 6,17 × 3,08 mm | 14,94 | 0,84 |
| Ellipse 3:1 | 8,51 × 2,84 mm | 18,95 | 0,66 |
| Rectangle plat 4:1 (type tube plat, un seul canal) | 10,0 × 2,5 mm | 25,00 | 0,50 |
| Goutte d'eau, lentille (type tube UMD) | à dimensionner numériquement | | |

Paroi : épaisseur constante (proposition 0,4 mm), contour extérieur = contour intérieur
décalé de l'épaisseur (angles extérieurs arrondis au rayon de l'épaisseur). Le périmètre
côté air est donc un peu plus grand que le périmètre côté propane ; on le reporte pour
chaque forme.

## 3. Batterie de référence (à valider)

| Paramètre | Proposition |
|---|---|
| Tube de référence | rond, Ø intérieur 4 mm, paroi 0,4 mm (Ø extérieur 4,8 mm) |
| Disposition | quinconce, triangle équilatéral |
| Pas transversal (rond) | 2 × Ø extérieur = 9,6 mm ; pas longitudinal = 0,866 × pas transversal |
| Nombre de rangs | 4 |
| Autres formes | mêmes 4 rangs et même disposition ; pas transversal multiplié par A_forme / A_rond pour garder la même section et le même périmètre totaux par unité de surface frontale |

La profondeur et le volume d'encombrement changent donc d'une forme à l'autre : ce sont
des **résultats**, comme chez Tancabel.

## 4. Simulation

| Paramètre | Proposition |
|---|---|
| Domaine | tranche 2D, un pas transversal de haut, conditions périodiques haut / bas |
| Tampons | amont 5 Ø, aval 10 Ø (à confirmer par l'étude de convergence) |
| Air | sec, 20 °C, propriétés constantes |
| Entrée | 1 m/s uniforme, température uniforme |
| Paroi | température imposée (propane en changement de phase), scalaire passif |
| Régime | Re ≈ 300 sur Ø extérieur à 1 m/s : laminaire, mais sillages instationnaires (lâcher de tourbillons dès Re ≈ 50 derrière un corps non profilé) → **solveur instationnaire (pimpleFoam), grandeurs moyennées dans le temps** ; comparaison avec le stationnaire (simpleFoam) sur le cas de référence |
| Maillage | étude de convergence sur le tube rond (3 maillages, GCI), puis réglage figé pour toutes les formes |

## 5. Grandeurs mesurées pour chaque cas

- Perte de charge Δp et puissance de ventilation par unité de surface frontale.
- Puissance échangée Q et coefficient d'échange h côté air (méthode UA-LMTD).
- Formes sans dimension : j (Colburn), f (Fanning), j / f.
- **Puissance de ventilation par watt échangé** : indicateur principal pour la machine.
- Profondeur et volume d'encombrement, masse de métal.
- Champs : vitesse, pression, température ; zones mortes, sillages, canaux en ligne droite.

## 6. Progression

**Niveau 0 : validation de la chaîne (résultats connus)**

| Cas | Référence |
|---|---|
| Canal entre plaques parallèles (ailette plate idéale) | solution exacte : f·Re = 24, Nu = 7,54 (paroi isotherme, établi) |
| Faisceau de tubes ronds en quinconce | corrélation de Zukauskas |
| Tube rond isolé | Hilpert / Churchill-Bernstein (Nu), nombre de Strouhal ≈ 0,2 |

Pour ces cas seulement, quelques vitesses supplémentaires (0,5 et 2 m/s) pour vérifier
la tendance face aux corrélations.

**Niveau 1 : forme du tube** à 1 m/s, critère d'équité de la section 2 : rond, carré,
losange, triangle pointe face à l'air, triangle base face à l'air, ellipses 2:1 et 3:1,
rectangle plat, goutte, lentille.

**Niveau 2 : agencement**, avec les 2 ou 3 meilleures formes : aligné / quinconce, pas
transversal et longitudinal, nombre de rangs (1, 2, 4, 8).

**Plus tard** : ailettes (plate, ondulée, persiennée, décalée, picots, en 3D), puis TPMS
avec orientation de la cellule, sous les mêmes règles.

## 7. À construire

- Chaîne 2D paramétrée : forme quelconque (contour intérieur + paroi), dimensionnement
  automatique selon la section 2, maillage, cas OpenFOAM, extraction, campagne avec reprise.
  Réutilise la logique de `outils/cfd_tpms`.
- Sorties dans un format réutilisable (paramètres + résultats + maillage) pour la base de
  l'optimisation bayésienne.

Ordre de grandeur : niveaux 0 à 2, environ 60 à 120 cas 2D, de quelques secondes à
quelques minutes chacun en stationnaire, nettement plus en instationnaire (à mesurer sur
le cas de référence).

## 8. Points à valider

1. Dh intérieur de 4 mm et paroi de 0,4 mm.
2. Batterie de référence (quinconce, 4 rangs, pas transversal = 2 Ø extérieur).
3. Liste des formes du niveau 1.
