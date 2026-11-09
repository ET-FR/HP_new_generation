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
| Faisceau de tubes ronds | bilan d'énergie air / paroi | 0,07 % | 0 | | validé |
| Tube isolé | Nu | 10,72 | Hilpert 9,89 ; Churchill-Bernstein 10,09 | +8 % ; +6 % | validé |
| Tube isolé | Strouhal (fréquence des tourbillons) | 0,220 (36,7 Hz) | Roshko 0,205 | +7 % | validé |
| Tube isolé | Cd (traînée) | 1,45 | essais ≈ 1,1 à 1,2 | surestimé, attendu en 2D | cohérent |

Conclusion : la chaîne (géométrie, maillage gmsh, conversion OpenFOAM, conditions
aux limites, solveurs, mesures) reproduit la solution exacte d'un écoulement laminaire établi
et les corrélations de référence d'un faisceau de tubes et d'un tube isolé (échange et
fréquence des tourbillons à moins de 10 %, dans l'incertitude des corrélations). Elle peut
servir au niveau 1. Reste à comparer la perte de charge du faisceau à une corrélation publiée.

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
| Facteur de frottement par rang (Zukauskas) | 0,456 |
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
