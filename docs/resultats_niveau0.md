# Résultats du niveau 0 : validation de la chaîne CFD 2D

Calculs du 9 novembre 2026, OpenFOAM v2606 (compilé dans le conteneur cloud), 4 cœurs.
Plan et conventions : `docs/plan_formes_simples.md`. Chaîne : `outils/cfd_2d/`.

Conditions communes : air à 20 °C, propriétés constantes, vitesse d'entrée 1 m/s, paroi à
température imposée (propane en changement de phase), température transportée comme scalaire
passif (entrée 0, paroi 1), écoulement laminaire.

## Synthèse

| Cas | Grandeur | CFD | Référence | Écart | Verdict |
|---|---|---|---|---|---|
| Plaques parallèles | f·Re (frottement établi) | 23,93 | 24 (exact) | −0,3 % | validé |
| Plaques parallèles | Nu (échange établi) | 7,529 | 7,541 (exact) | −0,2 % | validé |
| Faisceau de tubes ronds | Nu sur Ø 6 mm | 14,75 | Zukauskas : 11,25 à 15,54 | dans la fourchette, −5 % de la loi faisceau | validé |
| Faisceau de tubes ronds | perte de charge (4 rangs) | 4,40 Pa | Zukauskas (abaques) : 5,02 Pa | −12 % | cohérent (incertitude des abaques ±15 à 25 %) |
| Faisceau de tubes ronds | bilan d'énergie air / paroi | 0,07 % | 0 | | validé |
| Tube isolé | Nu | 10,72 | Hilpert 9,89 ; Churchill-Bernstein 10,09 | +8 % ; +6 % | validé |
| Tube isolé | Strouhal (fréquence des tourbillons) | 0,220 (36,7 Hz) | Roshko 0,205 | +7 % | validé |
| Tube isolé | Cd (traînée) | 1,45 | essais ≈ 1,1 à 1,2 | surestimé, attendu en 2D | cohérent |

Conclusion : la chaîne (géométrie, maillage gmsh, conversion OpenFOAM, conditions
aux limites, solveurs, mesures) reproduit la solution exacte d'un écoulement laminaire établi
et les corrélations de référence d'un faisceau de tubes et d'un tube isolé (échange et
fréquence des tourbillons à moins de 10 %, dans l'incertitude des corrélations). Elle peut
servir au niveau 1.

## 1. Plaques parallèles (ailette plate idéale)

Écartement 2 mm (Dh = 4 mm), longueur 200 mm, Re = 264, stationnaire (simpleFoam), 40 × 800
rectangles. Convergé en 1 138 itérations (résidus < 1e-7), 17 s de calcul.

- Profil de vitesse : plat à l'entrée, parabolique une fois établi, maximum 1,5 × la vitesse
  moyenne au centre (valeur exacte du laminaire entre plaques).
- Pression : baisse linéaire, environ 11 Pa sur 200 mm.
- Température : l'air atteint presque la température des plaques vers 100 mm ; au-delà, la
  plaque n'échange presque plus. **Information de conception** : à 1 m/s et 2 mm d'écartement,
  une ailette plate plus profonde qu'environ 50 à 100 mm est peu utile.

Figures : `docs/resultat_niveau0_plaques.png` (profils et comparaison à l'exact),
`docs/cfd_plaques_champs.png` (cartes de vitesse, température, pression).

## 2. Faisceau de tubes ronds (référence du niveau 1)

Tubes Ø 6 mm extérieur (canal 4 mm, paroi 1 mm), quinconce, pas 12 × 10,4 mm, 4 rangs.
Vitesse maximale entre les tubes 2 m/s, Re_max = 792. Instationnaire (pimpleFoam), 0,63 s
simulées dont 0,38 s moyennées (environ 25 périodes de lâcher de tourbillons), 28 min de calcul.

| Grandeur | Valeur |
|---|---|
| Perte de charge (4 rangs) | 4,40 Pa |
| Facteur de frottement par rang (définition de Zukauskas) | 0,456 |
| Température de mélange en sortie (efficacité) | 0,281 (28,1 %) |
| NTU | 0,330 |
| Coefficient d'échange h | 63,6 W/m²·K |
| Nu sur Ø 6 mm | 14,75 |
| j de Colburn (vitesse maximale) | 0,0209 |
| Bilan d'énergie (paroi / air) | −0,07 % |
| Stabilité de la moyenne (1re / 2e moitié) | 0,05 % |

Zukauskas, 4 rangs (C2 = 0,89) : 11,25 avec la loi « cylindre isolé » qu'il recommande pour
100 < Re < 1 000, 15,54 avec la loi des faisceaux 1 000 < Re < 2·10⁵ prolongée. Re_max = 792
est proche de la frontière ; la CFD (14,75) est dans la fourchette, plus proche de la loi des
faisceaux, ce qui est cohérent avec un faisceau serré.

Perte de charge comparée à Zukauskas (Advances in Heat Transfer, vol. 8, 1972), méthode
Δp = N_L · χ · f · ρ·V_max²/2 avec f et χ lus sur les abaques, numérisés par la bibliothèque
libre `ht` (fonction `dP_Zukauskas`, Caleb Bell ; mêmes abaques qu'Incropera, fig. 7.14) :
f = 0,521 par rang et Δp = 5,02 Pa, contre f = 0,456 et Δp = 4,40 Pa en CFD (−12 %).
L'écart est dans l'incertitude des abaques (lecture graphique, essais sur des faisceaux de
nombreux rangs, en soufflerie avec turbulence résiduelle) ; un calcul 2D laminaire, sans
turbulence amont ni effets 3D, donne attendu une perte de charge un peu plus faible.
Corrélation de Gaddis-Gnielinski (VDI Heat Atlas) non utilisée : formules non accessibles
depuis la session ; à ajouter si l'on dispose de l'ouvrage.

Observations : jets entre les tubes jusqu'à 3 m/s, sillages lents derrière chaque tube,
lâcher de tourbillons surtout après le dernier rang. Les mailles du tampon aval (1 mm)
amortissent les tourbillons trop vite ; sans effet sur les mesures (prises dans le noyau et à
la sortie), mais à affiner si l'on veut étudier le sillage.

Figure : `docs/resultat_niveau0_faisceau_rond.png`.

## 3. Tube rond isolé

Tube Ø 6 mm seul, domaine 40 Ø × 20 Ø (blocage 5 %), Re = 396, instationnaire (pimpleFoam),
86 929 mailles dont 20 couches de quadrilatères contre la paroi. 0,99 s simulées, moyenne sur
les 0,60 dernières secondes (22 périodes), 1 h 38 de calcul.

| Grandeur | CFD | Référence | Écart |
|---|---|---|---|
| Nu moyen | 10,72 | Hilpert 9,89 ; Churchill-Bernstein 10,09 | +8 % ; +6 % |
| Strouhal | 0,220 (36,7 Hz) | Roshko 0,205 | +7 % |
| Cd moyen | 1,45 | essais ≈ 1,1 à 1,2 | surestimé |
| Cl efficace | 0,78 | | |
| Stabilité de la moyenne | Cd 0,07 % ; Nu 0,02 % | | |

Lecture : allée de tourbillons de Bénard-von Kármán régulière (un seul pic de fréquence),
zone de recirculation derrière le tube, chaleur emportée par paquets dans les tourbillons.
L'échange et la fréquence sont à moins de 10 % des corrélations, dans leur incertitude. La
traînée est surestimée, comme toujours en 2D au-delà de Re ≈ 190 : le sillage réel devient
tridimensionnel et moins organisé, ce qu'un calcul 2D ne peut pas représenter ; le blocage de
5 % y contribue un peu. Conséquence pour la suite : les comparaisons **entre formes** en 2D
restent valables, mais les valeurs absolues de traînée et de perte de charge des formes non
profilées sont probablement un peu surestimées.

Figure : `docs/resultat_niveau0_tube_isole.png`.

## 4. Convergence en maillage (faisceau de tubes ronds)

Trois maillages de même règle de construction (`maillage.py`, paramètre `finesse` 0,667 / 1 /
1,5), rapport de raffinement linéaire ≈ 1,4 à 1,5. Méthode GCI de Celik et al. (2008),
`outils/cfd_2d/convergence.py` (vérifiée sur l'exemple de l'article : p = 1,53, GCI 2,2 %).

| Grandeur | Grossier (8 412) | Référence (17 480) | Fin (38 286) | R = e21/e32 | Verdict |
|---|---|---|---|---|---|
| Δp (Pa) | 4,272 | 4,396 | 4,397 | 0,01 | **convergé** : référence / fin 0,03 % |
| Nu (Ø 6 mm) | 14,93 | 14,75 | 14,20 | 3,1 | **non convergé** : référence / fin −3,8 % |
| T de sortie | 0,284 | 0,281 | 0,272 | 3,2 | non convergé : −3,2 % |
| h (W/m²·K) | 64,4 | 63,6 | 61,2 | 3,1 | non convergé : −3,8 % |

Durées : grossier 41 min (deux fois plus de pas de temps que la référence, à cause de petites
mailles déformées là où les tubes touchent les bords haut et bas), référence 28 min, fin 59 min.

Lecture :
- La **perte de charge** est convergée dès le maillage de référence.
- L'**échange** ne l'est pas : il baisse quand on raffine, et l'écart grandit (R > 1), signe
  que la couche limite thermique contre les tubes est encore insuffisamment résolue par des
  triangles de 0,08 mm. On n'est pas dans le domaine asymptotique : le GCI et la valeur
  extrapolée ne sont pas utilisables pour Nu. Le maillage de référence surestime l'échange
  d'au moins 4 %, probablement 5 à 8 % par rapport à la valeur convergée.
- Nu reste dans la fourchette de Zukauskas sur les trois maillages ; la validation du
  niveau 0 tient, mais la marge d'incertitude sur l'échange doit être portée à environ ±8 %.

Pistes pour le niveau 1 : mailler plus finement près des parois (le maillage « fin » coûte
environ 1 h par forme), ou ajouter des couches de quadrilatères contre les tubes (comme pour
le tube isolé), ce qui suppose de régler le défaut rencontré là où les couches des tubes coupés
rejoignent le raccordement haut / bas (165 faces à près de 90°).

Figure : `docs/convergence_faisceau_rond.png` ; données : `docs/resultats_niveau0/convergence_faisceau_rond.json` ;
archives : `resultats_cfd/convergence/`.

### 4 bis. Maillage à anneaux de couches (`maillage_couches.py`)

Autour de chaque tube, anneau structuré de quadrilatères (1re couche 0,01 mm, raison 1,15,
15 couches, 0,48 mm), puis triangles ; demi-anneaux coupés net sur les bords périodiques.
Qualité : non-orthogonalité max 27 à 33° (contre 43°), déformation max 0,5 (contre 2,1).
Trois finesses (0,7 / 1 / 1,4) :

| Grandeur | Couches grossier (17 868) | Couches moyen (32 042) | Couches fin (56 802) |
|---|---|---|---|
| Δp (Pa) | 4,384 | 4,281 | 4,481 |
| Nu (Ø 6 mm) | 14,46 | 14,38 | 14,18 |
| T de sortie | 0,276 | 0,275 | 0,272 |
| Durée de calcul | 15 min | 37 min | 1 h 48 |

Lecture :
- **Échange** : les deux familles de maillages, construites différemment, aboutissent à la même
  valeur sur leur maillage le plus fin (14,20 en triangles, 14,18 en couches). L'échange est
  donc établi à **Nu ≈ 14,2 ± 0,2** (±1,5 %). Le maillage de couches moyen le surestime de
  1,4 %, le grossier de 2 % ; le maillage de triangles de référence, lui, de 4 %.
- **Perte de charge** : toutes les valeurs (deux familles, six maillages) sont entre 4,28 et
  4,48 Pa, sans tendance nette (convergence « oscillante » au sens de Celik). Les écarts sont
  du niveau des fluctuations de l'écoulement instationnaire (écart-type de Δp sur 0,1 s :
  0,2 à 0,3 Pa) ; sur le maillage le plus fin, la moyenne bouge encore de 2 % entre les deux
  moitiés de la fenêtre. **Δp ≈ 4,4 ± 0,1 Pa** (±2,5 %), soit −12 % par rapport aux abaques
  de Zukauskas, dans leur incertitude.
- Le GCI de Celik ne s'applique pas ici (régime non asymptotique ou oscillant) ; la conclusion
  repose sur l'accord des deux familles de maillages et sur l'amplitude des écarts.

**Conclusion** : avec les anneaux de couches, l'échange et la perte de charge sont connus à
±2,5 % près dès le maillage moyen, contre ±8 % pour l'échange avec les triangles seuls. Le
maillage de couches est retenu pour la suite ; le choix entre finesse grossière (15 min par
cas, ±2,5 %) et moyenne (37 min, ±2 %) reste à faire pour le niveau 1.

Figure : `docs/convergence_faisceau_rond.png` (les deux familles) ; données :
`docs/resultats_niveau0/convergence_faisceau_rond_couches.json` ; archives :
`resultats_cfd/convergence/rond_couches_*.tar.xz`.

## Données conservées

Le conteneur de calcul est temporaire. Chaque cas terminé est archivé dans
`resultats_cfd/niveau0/<cas>.tar.xz` (`outils/cfd_2d/archiver.py`) : cas complet relançable
(maillage, conditions, réglages), dernier pas de temps (champs instantanés et moyennés),
séries temporelles des mesures, résultats extraits, extraits des journaux.

Pour rouvrir un cas :

```bash
tar xJf resultats_cfd/niveau0/rond.tar.xz
```
```bash
cd rond && foamToVTK -latestTime    # puis ouvrir VTK/ dans ParaView
```

Résultats chiffrés seuls : `docs/resultats_niveau0/<cas>.json`.
