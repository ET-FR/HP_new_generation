# Échangeur cylindrique à flux radial

Nouvelle architecture du module échangeur + ventilateur (12/11/2026), après l'abandon du canal en hélice Ø 150
(trop peu de section de passage : 45 m³/h à 30 Pa, voir `../cylindre_d150_helice/`).

Principe modélisé en 3D, **variante A′** : cylindre couché Ø 200 × 400 mm (450 jusqu'au 12/11 au soir). L'air est aspiré à travers un manchon filtrant
puis une galette d'échangeur plissée en étoile sur 280°. Il se rassemble dans la chambre centrale vide, passe la
gorge et une volute qui remonte au-dessus du cylindre. Des ventilateurs du commerce, placés juste avant la bouche,
le rejettent vers l'avant.

| Fichier | Contenu |
|---|---|
| `echangeur_radial.html` | Document unique : modèle 3D interactif de A′ (pièces activables, plan de coupe), puis croquis 2D à l'échelle : variante D (proposée : soufflage par le haut, ventilateur dans la cheminée, bac à condensats), A′, A (tangentiel), B et C, filtre et vitesses |
| `echangeur_radial.FCStd`, `.step`, `*.stl` | Modèle FreeCAD et exports, sans les tubes de réfrigérant |
| `dimensions.json` | Cotes et surfaces calculées par le script |
| `vue_ensemble.png`, `vue_bout.png` | Rendus |

Scripts : `outils/cad/echangeur_radial.py` (modèle, paramètres dans `outils/cad/parametres_radial.json`),
`outils/cad/html_radial.py` (page complète ; elle inclut les croquis de `outils/croquis/croquis_radial.py`).

Reste à faire : tubes plats et collecteurs dans les plis, choix des ventilateurs (2 × Ø 160 de principe sont
trop petits pour 2 500 m³/h), CFD 2D de la coupe (répartition du débit pli par pli, pertes de charge), puis
température de condensation et débit côté extérieur (choix b : condenser plus chaud plutôt qu'agrandir).

**Variante D** (12/11, dessin de l'utilisateur, croquis seulement) : appareil en selle sous l'ouvrant, échangeur sur 2 × 105°,
bas fermé au-dessus d'un bac à condensats vidé par le pont, cheminée verticale (col 150 mm, ventilateur dedans, convergent) et
fente de sortie 50 × 400 mm avec volet (vertical en clim, incliné vers la pièce en chauffage).

**Variante E** (12/11, dessin de l'utilisateur vu de dessus, croquis seulement) : tube Ø 100 cintré en fer à cheval, branches
contre la vitre ; plénum central dont tout le dessus est la bouche (150 × 200 mm), ventilateur axial Ø 140 à axe vertical.
Encombrement 400 × 250 × 200 mm. Vitesses correctes (bouche 5–8 m/s) mais galette de 0,13 m² seulement : hA ≈ 110 W/K pour
≈ 600 requis côté pièce.
Modèle 3D de E (tubes nus, sans plis ni ailettes pour l'instant) dans `variante_e/` : script
`outils/cad/echangeur_fer_a_cheval.py` (paramètres `outils/cad/parametres_fer_a_cheval.json`). Tube **Ø 150** (Ø 100 dans
les croquis 2D), toujours dans 400 × 250 × 200 mm : 32 tubes de réfrigérant Ø 3 en tournesol (densité uniforme, pas d'or,
entraxe mini 13,6 mm) dans la zone r 20 → 73 mm sur 230° (de −90°, point le plus bas du cercle, à 140°), qui suivent le
fer à cheval, sans collecteurs ni bac ; socle (châssis) de 15 mm qui s'arrête sous le milieu du tube. Le plénum n'a plus que
100 × 100 mm (ventilateur Ø 90) : 24 m/s dans la bouche à 830 m³/h. hA des tubes nus (Zukauskas) ≈ 16 W/K à 830 m³/h pour
≈ 600 requis. Le document principal l'affiche dans une seconde vue 3D (maillage allégé `tubes_web.stl`, mètre et échelle) ;
rendus `vue_ensemble.png`, `vue_coupe.png`, `vue_dessus.png`.

**Variante F** (12/11, 3D seulement) : comme E, mais un seul tube droit Ø 150 × 394 couché le long de la vitre (la variante A′
avec un flux vers le haut). L'air entre par le côté pièce, le dessus et le dessous du tube, ressort côté vitre dans un plénum de
98 × 394 mm entre le tube et la vitre, et monte (3 axiaux Ø 90 à axe vertical, volet à lames). 32 tubes nus en tournesol,
socle jusqu'au milieu du tube, encombrement 259 × 400 × 200 mm. Bouche 4 à 6 m/s ; hA des tubes nus ≈ 12 W/K à 830 m³/h.
Script `outils/cad/echangeur_tube_droit.py` (paramètres `parametres_tube_droit.json`), fichiers dans `variante_f/`.
Vue de coupe de F avec lamelles (12/11) : tranche de 24 mm, 20 lamelles d'aluminium de 0,12 mm au pas de 1,2 mm (secteur
d'anneau r 20 → 73 mm sur 230°, percées pour les 32 tubes). Sur tout le tube : 328 lamelles, 6,3 m², hA ≈ 560 W/K et
Δp ≈ 40 Pa à 830 m³/h (ordre de grandeur). Fichiers `variante_f/tranche_*.stl`, `tranche_lamelles.step`, rendus
`tranche_coupe.png`, `tranche_bout.png`, `tranche_detail.png`.
Vue de coupe de F plissée (12/11, corrigée) : même tranche de 24 mm ; chaque lamelle (0,10 mm au pas de 1,0 mm) est une
plaque pleine à bord extérieur en zigzag (8 dents de 6 mm, rainures jusqu'à r = 45 mm, pointes à 73 mm) et bord intérieur
rond (r = 25 mm) ; 32 tubes en tournesol sur toute la lamelle (entraxe mini 11 mm). Contour d'entrée 0,188 m², 4,8 m² de
lamelles sur tout le tube ; estimation ≈ 560 W/K et ≈ 55 Pa à 830 m³/h (≈ 430 W/K, ≈ 45 Pa au pas de 1,2 mm).
Fichiers `variante_f/plis_*.stl`, `tranche_plissee.step`, rendus `plis_coupe.png`, `plis_bout.png`, `plis_detail.png`.

**Concept imprimé** (12/11, `variante_f/imprime/`, script `outils/cad/concept_imprime.py`) : deux tranches de 25 mm, sans et
avec stries (10 dents triangulaires, rainures jusqu'à r = 70 mm). Tube Ø 200, parois ≥ 1 mm, noyau vide jusqu'à r = 45 mm,
32 canaux de propane Ø 2,2 chacun dans un profil elliptique 11 × 4,2 mm aligné avec l'air, répartis en tournesol sur tout
le disque (dents comprises) ; lamelles de 1 mm au jeu de 1,5 mm en couronnes de 5 mm décalées d'un demi-pas, une sur deux
sous r = 60 mm. Bord d'entrée 393 mm sans stries, 621 mm avec. Formes de principe à comparer en CFD. Rendus `imp_*.png`.
