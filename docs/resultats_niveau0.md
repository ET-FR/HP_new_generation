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
| Tube isolé | Cd, Strouhal, Nu | en cours | Hilpert, Churchill-Bernstein, Roshko | | en cours |

Conclusion à ce stade : la chaîne (géométrie, maillage gmsh, conversion OpenFOAM, conditions
aux limites, solveurs, mesures) reproduit la solution exacte d'un écoulement laminaire établi
et la corrélation de référence d'un faisceau de tubes. Elle peut servir au niveau 1.

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

En cours (pimpleFoam, 0,99 s simulées, environ 2 h 30 de calcul).

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
