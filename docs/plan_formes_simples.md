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
| Paroi | **1 mm** d'épaisseur constante (décidé le 9 novembre 2026) |
| Batterie de référence | validée (section 3) |
| Formes du niveau 1 | validées pour le moment ; la liste sera complétée plus tard |

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

Paroi : épaisseur constante de **1 mm**, contour extérieur = contour intérieur décalé de
1 mm (angles extérieurs arrondis au rayon de 1 mm). Pour une forme convexe, le périmètre
extérieur vaut exactement P_int + 2π·e = P_int + 6,28 mm par tube.

Conséquence : le périmètre **côté propane** (intérieur) est identique pour toutes les formes,
mais le périmètre **côté air** (extérieur) ne l'est pas, car le nombre de tubes change. Il
baisse jusqu'à 17 % pour le tube plat (tableau de la section 3). On garde l'égalité côté
propane (elle découle de la charge et du Dh) et on reporte la surface côté air comme résultat.

Résistance thermique de la paroi : 1 mm d'aluminium (λ ≈ 150 W/m·K) ajoute environ
7e-6 m²·K/W, négligeable devant la résistance côté air (≈ 1e-2 m²·K/W) : la paroi à
température imposée reste une bonne hypothèse.

## 3. Batterie de référence (validée)

| Paramètre | Proposition |
|---|---|
| Tube de référence | rond, Ø intérieur 4 mm, paroi 1 mm (Ø extérieur 6 mm) |
| Disposition | quinconce, triangle équilatéral |
| Pas transversal (rond) | 2 × Ø extérieur = 12 mm ; pas longitudinal = 0,866 × pas transversal = 10,4 mm |
| Nombre de rangs | 4 |
| Autres formes | mêmes 4 rangs et même disposition ; pas transversal multiplié par A_forme / A_rond pour garder la même section et le même périmètre totaux par unité de surface frontale |

La profondeur et le volume d'encombrement changent donc d'une forme à l'autre : ce sont
des **résultats**, comme chez Tancabel.

Dimensions obtenues (mm ; enveloppe extérieure approchée, à recalculer exactement par la chaîne) :

| Forme | Pas transv. | Pas long. | Largeur ext. (face à l'air) | Longueur ext. (sens de l'air) | Périmètre côté air total / rond | Profondeur 4 rangs |
|---|---|---|---|---|---|---|
| Rond | 12,0 | 10,4 | 6,0 | 6,0 | 1,00 | 37 |
| Carré | 15,3 | 13,2 | 6,0 | 6,0 | 0,93 | 46 |
| Losange | 15,3 | 13,2 | 7,7 | 7,7 | 0,93 | 47 |
| Triangle (2 orientations) | 19,8 | 17,2 | 8,9 | 8,0 | 0,87 | 60 |
| Ellipse 2:1 | 14,3 | 12,4 | 5,1 | 8,2 | 0,95 | 45 |
| Ellipse 3:1 | 18,1 | 15,7 | 4,8 | 10,5 | 0,89 | 58 |
| Rectangle plat 4:1 | 23,9 | 20,7 | 4,5 | 12,0 | 0,83 | 74 |

Toutes les formes passent sans chevauchement. Les formes à gros canal (triangle, tube plat)
sont moins nombreuses, plus espacées et donnent une batterie plus profonde : à charge égale,
le volume d'encombrement peut presque doubler. C'est un résultat de l'étude, pas un défaut
du critère.

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

Maillages prêts (9 novembre 2026, `outils/cfd_2d/cas_validation.py`, figure
`docs/maillages/validation_niveau0.png`) :
- plaques : écartement 2 mm (Dh = 4 mm), longueur 200 mm, 40 × 800 quadrilatères
  resserrés vers les parois ;
- tube isolé : Ø 6 mm, domaine 40 Ø × 20 Ø (blocage 5 %), 20 couches de quadrilatères
  contre la paroi (1re couche 0,01 mm, raison 1,15), sillage raffiné sur 12 Ø ;
- faisceau de tubes ronds : cas « rond » du niveau 1 (`docs/maillages/formes_niveau1.png`).

**Niveau 1 : forme du tube** à 1 m/s, critère d'équité de la section 2 : rond, carré,
losange, triangle pointe face à l'air, triangle base face à l'air, ellipses 2:1 et 3:1,
rectangle plat, goutte, lentille.

**Niveau 2 : agencement**, avec les 2 ou 3 meilleures formes : aligné / quinconce, pas
transversal et longitudinal, nombre de rangs (1, 2, 4, 8).

**Plus tard** : ailettes (plate, ondulée, persiennée, décalée, picots, en 3D), puis TPMS
avec orientation de la cellule, sous les mêmes règles.

## 7. Calcul

Décidé le 9 novembre 2026 : niveaux 0 et 1 calculés dans le conteneur cloud de la session
(4 cœurs), avec **OpenFOAM v2606** compilé depuis les sources
(`outils/openfoam/installer_v2606.sh`, 2 à 3 h). AWS envisagé plus tard pour la 3D et
l'optimisation bayésienne. Résultats (tableaux, figures, paramètres) poussés au fil de l'eau ;
champs bruts hors dépôt (recalculables).

Chaîne : `outils/cfd_2d/` — `geometrie.py` (formes, critère d'équité), `maillage.py` et
`cas_validation.py` (gmsh), `polymesh.py` (maillage OpenFOAM extrudé d'une maille, raccordement
cyclique haut / bas), `creer_cas.py` (cas complet : conditions aux limites, solveur, mesures).

Durées physiques simulées (instationnaire) : traversée du domaine + environ 25 périodes de
lâcher de tourbillons, moyenne temporelle après la phase de démarrage. Tube isolé : 0,99 s
(moyenne à partir de 0,39 s) ; batterie de tubes ronds : 0,63 s (moyenne à partir de 0,25 s).

## 8. À construire

- Chaîne 2D paramétrée : forme quelconque (contour intérieur + paroi), dimensionnement
  automatique selon la section 2, maillage, cas OpenFOAM, extraction, campagne avec reprise.
  Réutilise la logique de `outils/cfd_tpms`.
- Sorties dans un format réutilisable (paramètres + résultats + maillage) pour la base de
  l'optimisation bayésienne.

Ordre de grandeur : niveaux 0 à 2, environ 60 à 120 cas 2D, de quelques secondes à
quelques minutes chacun en stationnaire, nettement plus en instationnaire (à mesurer sur
le cas de référence).

## 9. Points validés et restant ouverts

Validés le 9 novembre 2026 : paroi de 1 mm, batterie de référence, liste des formes du
niveau 1 (provisoire).

Ouvert : Dh intérieur de 4 mm (conservé par défaut ; avec la paroi de 1 mm, le tube rond
fait 6 mm de diamètre extérieur).

## 10. Pistes en attente

**Tubes parallèles à l'air** (écoulement longitudinal), notée le 10 novembre 2026, mise de côté.
Estimation analytique (`outils/analytique/tubes_longitudinaux.py`, page 7 du rapport) : à charge
égale, la courbe suit le front de Pareto des formes en travers (un peu au-dessus à pas serré,
P ≤ 9 mm). Résultat **non validé** : anneau équivalent peu fidèle sous P/D ≈ 1,5, bouts de tubes
modélisés par des pertes forfaitaires, laminaire supposé, collecteurs non comptés.
À reprendre par une CFD 3D d'une cellule périodique (P = 8, 10, 12 mm, 1 m/s, bouts plats puis
profilés), puis le dessin d'un collecteur imprimé, qui décidera de la piste.

**Distributeur imprimé à orifices calibrés** (détente et répartition), notée le 10 novembre 2026.
Idée de départ : utiliser l'échangeur comme détendeur (plusieurs entrées donnant des Δp différents
selon la demande). Une détente répartie dans l'évaporateur est écartée : la température du propane
suit sa pression, le début de l'échangeur resterait chaud et la surface utile chuterait.
Piste retenue : avec 20 à 40 circuits en parallèle (voir l'estimation de charge,
`outils/analytique/charge_propane.py`), imprimer un **orifice calibré à l'entrée de chaque circuit**,
qui assure la répartition et une partie de la détente ; garder un détendeur électronique en amont
pour la surchauffe et l'inversion de cycle. Effet attendu : répartition égale entre circuits,
collecteur d'entrée en diphasique léger (moins de charge). À évaluer à l'étape 4 dans le modèle
de la machine, avec le volume des collecteurs.
Idées voisines à chiffrer au même moment : échangeur interne ligne liquide / aspiration (quelques %
de COP selon la littérature pour le propane) et éjecteur (≈ 3 à 5 % pour le propane, difficile à
régler à faible puissance).
