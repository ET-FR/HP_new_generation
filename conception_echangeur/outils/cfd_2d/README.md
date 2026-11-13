# CFD 2D côté air : formes simples et validation

Ce dossier contient la chaîne de simulation 2D qui sert à **comprendre l'effet de la géométrie
des tubes sur l'écoulement d'air et sur l'échange de chaleur** de la batterie d'une PAC de
fenêtre au propane, avant toute optimisation.

Documents liés :
- plan d'étude et décisions : `docs/plan_formes_simples.md`
- résultats du niveau 0 : `docs/resultats_niveau0.md`
- méthode d'optimisation retenue pour la suite : `docs/methode_optimisation.md`

## 1. Pourquoi ce travail

Dans la batterie air / propane, l'essentiel de la résistance au transfert de chaleur est côté
air (environ 95 % dans le modèle du simulateur). La forme et l'agencement des tubes fixent
deux choses qui s'opposent : **l'échange** (plus il est élevé, plus la batterie peut être
petite) et **la perte de charge** (plus elle est élevée, plus le ventilateur consomme et fait
de bruit). Avant d'optimiser des formes complexes (tubes profilés, surfaces imprimées en 3D),
on étudie des formes simples pour :

1. **valider la chaîne de calcul** sur des cas dont la réponse est connue (niveau 0) ;
2. **comprendre les mécanismes** : sillages, jets, zones mortes, relance de la couche limite ;
3. **fixer des règles de comparaison** qui serviront aussi à l'optimisation.

## 2. Démarche

| Niveau | Contenu | État |
|---|---|---|
| 0 | Validation : plaques parallèles (solution exacte), faisceau de tubes ronds (Zukauskas), tube isolé (Hilpert, Roshko) | terminé, validé |
| 1 | Comparaison de 10 formes de tubes à charge de propane égale | maillages prêts |
| 2 | Agencement (aligné / quinconce, pas, nombre de rangs) avec les meilleures formes | à faire |
| plus tard | Ailettes (3D), puis surfaces TPMS | hors de ce dossier |

**Critère d'équité entre formes** (décidé par le porteur du projet) : même charge de propane et
même périmètre de contact air / propane par unité de surface frontale. Les deux ensemble
imposent le **même diamètre hydraulique intérieur** (4 mm) à toutes les formes ; chaque forme a
sa propre taille, et le nombre de tubes s'ajuste (moins de tubes pour les formes à gros canal).

## 3. Entrées (ce que l'on impose)

| Entrée | Symbole | Valeur de référence | Unité | Où elle est fixée |
|---|---|---|---|---|
| Forme du canal intérieur | | rond, carré, losange, triangle (2 orientations), ellipses 2:1 et 3:1, tube plat 4:1, goutte, lentille | | `geometrie.py`, `FORMES` |
| Diamètre hydraulique intérieur | Dh | 4 | mm | `geometrie.py`, `batterie(Dh=…)` |
| Épaisseur de paroi | e | 1 | mm | `geometrie.py`, `batterie(paroi=…)` |
| Disposition | | quinconce, triangle équilatéral | | `geometrie.py` |
| Nombre de rangs | N_L | 4 | | `geometrie.py`, `batterie(rangs=…)` |
| Pas transversal du tube rond | Pt | 2 × Ø extérieur = 12 | mm | `geometrie.py` ; les autres formes : × A_forme / A_rond |
| Pas longitudinal | Pl | 0,866 × Pt | mm | `geometrie.py` |
| Tampons amont / aval | | 5 Ø et 10 Ø (30 et 60 mm) | mm | `geometrie.py` |
| Vitesse frontale de l'air | U | 1 | m/s | `creer_cas.py --vitesse` |
| Air (20 °C, propriétés constantes) | ν, ρ, cp, Pr | 1,516e-5 m²/s ; 1,204 kg/m³ ; 1006 J/kg·K ; 0,71 | | `creer_cas.py`, `AIR` |
| Température de paroi / d'entrée | T | 1 / 0 (adimensionnel) | | `creer_cas.py`, conditions aux limites |
| Régime | | laminaire ; stationnaire (plaques) ou instationnaire (tubes) | | `creer_cas.py` |
| Durée simulée (instationnaire) | | 2 traversées du domaine + ≈ 25 périodes de tourbillons | s | `creer_cas.py` (calcul automatique) |
| Maillage | | mailles de 0,08 mm à la paroi, 0,6 mm dans le noyau, 1 mm dans les tampons | mm | `maillage.py` |

Grandeur déduite des entrées, utile pour situer le régime : le **nombre de Reynolds**
Re = U × D / ν (environ 400 sur le tube de 6 mm à 1 m/s, environ 800 avec la vitesse maximale
entre les tubes). Ce n'est pas un résultat de la simulation.

## 4. Sorties (ce que la simulation calcule)

**Grandeurs principales** (moyennes dans le temps pour les cas instationnaires) :

| Sortie | Symbole | Unité | Définition | Ce qu'elle dit |
|---|---|---|---|---|
| Perte de charge | Δp | Pa | pression moyenne entrée − sortie | coût en ventilation (puissance, bruit) |
| Température de mélange en sortie | T_s | − | moyenne pondérée par le débit ; 0 = air entrant, 1 = paroi | efficacité de la batterie |
| Nombre d'unités de transfert | NTU | − | −ln(1 − T_s) | taille thermique |
| Coefficient d'échange côté air | h | W/m²·K | ṁ·cp·NTU / A_air (méthode UA-LMTD) | qualité de l'échange par m² |
| Nombre de Nusselt | Nu | − | h × D / k_air | échange comparé à la conduction seule, comparable aux corrélations |
| Facteur de Colburn | j | − | h / (ρ·U_max·cp) × Pr^(2/3) | échange sans dimension |
| Facteur de frottement | f | − | Δp / (N_L × ½ ρ U_max²) (faisceaux) ; Δp·Dh / (2 ρ U² L) (plaques) | frottement sans dimension |
| Rapport j / f | | − | | échange obtenu pour peu de frottement |
| Puissance de ventilation par watt échangé | P_vent / Q | 1/K | Δp × débit / Q | indicateur principal pour la machine |
| Profondeur de la batterie | | mm | | encombrement, à charge égale |

**Spécifiques au tube isolé** :

| Sortie | Symbole | Définition |
|---|---|---|
| Coefficient de traînée | Cd | effort dans le sens de l'air / (½ ρ U² × D × épaisseur) |
| Portance efficace | Cl | écart-type de l'effort transversal (oscillation due aux tourbillons) |
| Nombre de Strouhal | St | fréquence des tourbillons × D / U |

**Champs complets** (en chaque maille, instantanés et moyennés) : vitesse U, pression p,
température T et son gradient. Ce sont eux qui donnent les cartes : jets, sillages, zones
mortes, réchauffement de l'air.

**Contrôles de qualité** (ce ne sont pas des résultats physiques, mais la preuve que les
résultats sont fiables) :

| Contrôle | Calcul | Seuil |
|---|---|---|
| Bilan d'énergie | chaleur cédée par la paroi comparée à la chaleur emportée par l'air | < 1 % |
| Stabilité de la moyenne | écart entre la 1re et la 2e moitié de la fenêtre de moyenne | < 1 % (sinon prolonger) |
| Qualité du maillage | checkMesh : non-orthogonalité, déformation | « Mesh OK », non-orthogonalité < 70° |

## 5. Résultats obtenus (niveau 0)

| Cas | Sortie | CFD | Référence | Écart |
|---|---|---|---|---|
| Plaques parallèles | f·Re | 23,93 | 24 (exact) | −0,3 % |
| Plaques parallèles | Nu | 7,529 | 7,541 (exact) | −0,2 % |
| Faisceau de tubes ronds | Nu (Ø 6 mm) | 14,75 | Zukauskas 11,25 à 15,54 (±15 à 25 %) | dans la fourchette |
| Faisceau de tubes ronds | Δp (4 rangs) | 4,40 Pa | Zukauskas (abaques, bibliothèque `ht`) 5,02 Pa | −12 % |
| Faisceau de tubes ronds | bilan d'énergie | 0,07 % | | |
| Tube isolé | Nu | 10,72 | Hilpert 9,89 ; Churchill-Bernstein 10,09 | +8 % ; +6 % |
| Tube isolé | Strouhal | 0,220 | Roshko 0,205 | +7 % |
| Tube isolé | Cd | 1,45 | essais ≈ 1,1 à 1,2 | surestimé (2D) |

Détails, figures et interprétation : `docs/resultats_niveau0.md`.

## 6. La chaîne, fichier par fichier

| Fichier | Rôle |
|---|---|
| `geometrie.py` | Formes, dimensionnement au Dh imposé, paroi, batterie en quinconce |
| `maillage.py` | Maillage gmsh d'une batterie, bords haut / bas périodiques |
| `cas_validation.py` | Maillages des cas de validation (plaques, tube isolé) |
| `export_gmsh.py` | Lecture du maillage gmsh (noeuds, cellules, bords) |
| `polymesh.py` | Écriture du maillage OpenFOAM (extrusion d'une maille, raccordement cyclique) |
| `creer_cas.py` | Cas OpenFOAM complet : conditions aux limites, solveur, mesures |
| `extraire.py` | Calcul des sorties et comparaison aux références |
| `archiver.py` | Archive compacte d'un cas terminé (`resultats_cfd/`) |
| `figure_*.py` | Figures : maillages, résultats, cartes de champs |

Outils : Python (numpy, shapely, gmsh, pyvista, matplotlib) et OpenFOAM v2606
(`outils/openfoam/installer_v2606.sh`).

## 7. Utilisation

```bash
source /opt/openfoam/OpenFOAM-v2606/etc/bashrc
```
```bash
python outils/cfd_2d/creer_cas.py --cas batterie --forme rond --dossier cas/rond
```
```bash
bash cas/rond/Allrun
```
```bash
python outils/cfd_2d/extraire.py cas/rond --json cas/rond/resultat.json
```
```bash
python outils/cfd_2d/archiver.py cas/rond resultats_cfd/niveau1/rond.tar.xz
```

Cas disponibles : `--cas plaques`, `--cas tube_isole`, `--cas batterie --forme <forme>`.

Durées mesurées (4 cœurs) : plaques 20 s ; faisceau de tubes ronds 28 min ; tube isolé
1 h 38.

## 8. Limites connues

- 2D : pas d'effets de bout, pas d'ailettes, sillage réel légèrement 3D à Re ≈ 400
  (le calcul 2D surestime un peu la traînée du tube isolé).
- Air sec, propriétés constantes : pas de condensation ni de givre.
- Paroi à température imposée : valable pour un tube à paroi épaisse et un propane en
  changement de phase ; à revoir pour des ailettes (conduction dans le métal).
- Faisceaux, convergence en maillage (tubes ronds) : avec les triangles seuls, l'échange
  n'est pas convergé (±8 %). Avec les anneaux de couches (`--couches`, `maillage_couches.py`),
  échange et perte de charge sont connus à ±2,5 % (Nu ≈ 14,2, Δp ≈ 4,4 Pa) ; les écarts
  restants sont du niveau des fluctuations de l'écoulement instationnaire. Voir
  `docs/resultats_niveau0.md`, sections 4 et 4 bis.
- Tampon aval à mailles de 1 mm : les tourbillons y sont amortis trop vite (sans effet sur
  les mesures, prises dans le noyau et à la sortie).
