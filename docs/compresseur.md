# Compresseur : synthèse et cahier des charges

Objectif du projet : PAC de fenêtre réversible R290, 1500 €, COP 5 à 6, petite
taille. Cette note mesure ce que le compresseur coûte au COP, fixe les
rendements à exiger et propose une cylindrée. Les tableaux détaillés sont
dans [`resultats_compresseur.md`](resultats_compresseur.md), régénérés par :

```bash
python outils/etude_compresseur.py -o docs/resultats_compresseur.md
```

Comparaisons à **puissance fixée** (la régulation cherche la fréquence).
Compresseur **générique** du simulateur : les chiffres absolus seront à
refaire avec une carte constructeur, les tendances et ordres de grandeur sont
ce qui compte ici.

## 1. Ce que le compresseur coûte aujourd'hui

| Point | f (tr/s) | PR | η global | COP perdu par le compresseur | COP unité |
|---|---|---|---|---|---|
| Chauffage 7/20, 1,6 kW | 28 | 2,4 | 0,62 | 35 % | 4,9 |
| Chauffage 7/20, 3,2 kW | 60 | 2,9 | 0,65 | 32 % | 4,2 |
| Clim 35/27, 2,6 kW sensible | 52 | 2,6 | 0,65 | 35 % | 3,7 |

η global = η_is · η_mot · η_var (puissance isentropique / puissance
électrique du compresseur). Le compresseur et son moteur font perdre environ
un tiers du COP du cycle. C'est le plus gros poste après les pincements des
échangeurs.

Points clés :

* **Taux de compression faibles** (2,2 à 3,1) aux points qui comptent pour
  l'objectif. Un rotatif de climatiseur est souvent optimisé pour PR 3 à 3,5
  (conditions ASHRAE / ARI). Il faut un compresseur dont le meilleur
  rendement tombe vers PR 2,5.
* **Basses vitesses** (20 à 30 tr/s) à charge partielle, là où le COP 5 à 6
  est atteignable : c'est là que le moteur et les fuites internes pénalisent
  le plus. Le rendement à 20 à 40 tr/s est le critère de choix, pas le
  rendement au point nominal du catalogue.

## 2. Rendement global à exiger

η global requis (cycle figé, approximation) :

| Point | Échangeurs | COP 5 | COP 5,5 | COP 6 |
|---|---|---|---|---|
| Chauffage 7/20, 1,6 kW | actuels | 0,63 | 0,70 | 0,77 |
| Chauffage 7/20, 3,2 kW | actuels | 0,80 | 0,89 | 0,99 |
| Clim 35/27, 2,6 kW sens. | actuels | 0,90 | 1,00 | 1,11 |
| Chauffage 7/20, 1,6 kW | améliorés | 0,53 | 0,59 | 0,65 |
| Chauffage 7/20, 3,2 kW | améliorés | 0,64 | 0,72 | 0,80 |
| Clim 35/27, 2,6 kW sens. | améliorés | 0,64 | 0,72 | 0,79 |

« améliorés » : UA x2 et débits d'air x1,5 (voir README, objectif).

Ordre de grandeur réaliste pour un petit rotatif BLDC R290 : η global 0,62 à
0,68 pour un bon modèle du commerce, 0,70 à 0,72 pour le meilleur de sa
catégorie (η_is ≈ 0,78, moteur IPM ≈ 0,95, variateur ≈ 0,98). Un η global
supérieur à 0,75 n'est pas réaliste pour un rotatif de cette taille.

Conclusions :

1. **Avec les échangeurs actuels, le compresseur ne suffit pas** : COP 5 à
   pleine charge demanderait η global 0,80 ou plus. Seule la charge partielle
   en chauffage atteint 5 (η 0,63 à 0,70).
2. **Avec les échangeurs améliorés**, un compresseur à η global ≈ 0,70 donne
   COP 5 à 5,5 à pleine charge (chauffage 7 °C et clim 35 °C) et environ 6 à
   charge partielle. **COP 6 à pleine charge reste hors de portée**
   (η 0,80 requis).
3. Gain de COP par point de rendement (sensibilité, chauffage 7/20 3,2 kW) :
   η_is 0,72 → 0,78 : +6 % ; η_mot 0,935 → 0,965 : +3 %.

## 3. Cylindrée

À débit d'air fixé, la cylindrée change peu le COP (± 2 % entre 10 et
24 cm³). Elle fixe surtout la **plage de modulation** :

| Cylindrée (cm³) | P mini à 7 °C, 15 tr/s (kW) | P maxi à -7 °C, 110 tr/s (kW) |
|---|---|---|
| 10 | 0,59 | 2,6 |
| 12 | 0,69 | 3,0 |
| 14 | 0,80 | 3,4 |
| 16 | 0,90 | 3,8 |
| 20 | 1,09 | 4,5 |

Pour une pièce de 50 m² bien isolée, la charge à 7 °C est souvent sous 1 kW.
En dessous de la puissance mini, le compresseur cycle (perte Cd = 0,15 dans
le modèle). **Recommandation : 12 à 14 cm³**, f_min 10 à 15 tr/s,
f_max 110 à 120 tr/s. C'est aussi un compresseur plus petit et plus léger,
cohérent avec la petite taille. 16 cm³ seulement si une puissance de 3,5 kW
à -7 °C est exigée.

Constat annexe : avec la loi actuelle du simulateur, les ventilateurs suivent
la fréquence du compresseur. Un compresseur plus petit tourne plus vite à
même puissance, donc ventile plus, et paraît meilleur à tort (jusqu'à +10 %
en clim à charge partielle). La loi de ventilation doit être optimisée
indépendamment du compresseur (étape suivante possible : chercher le débit
optimal à chaque point).

## 4. Candidats du marché (à vérifier sur fiches officielles)

Informations de distributeurs et places de marché, conditions d'essai souvent
non précisées : **non exploitables telles quelles** pour le simulateur.

| Modèle (marque annoncée) | Type | Cylindrée | Données annoncées | Prix annoncé |
|---|---|---|---|---|
| GMCC DTN180D32UFZ | rotatif bicylindre DC inverter R290 | 18,1 cm³ | 3,18 kW, 785 W, COP 4,05 | n.d. |
| GMCC DTN210D32UFZ | rotatif bicylindre DC inverter R290 | 21 cm³ | 3,68 kW, 897 W, COP 4,10 | 103 à 143 $ |
| GMCC EDTN210D32EFZ | rotatif DC inverter R290, PAC | 21 cm³ | 12 à 120 tr/s, refoulement max 115 °C | 108 à 148 $ |
| GMCC DSM180D19UDZ | rotatif DC inverter | 18 cm³ | 30 à 120 tr/s, hauteur 302 mm | n.d. |
| Highly PTL232SDN | rotatif DC inverter R290 | n.d. | 3,85 kW | n.d. |

Lecture :

* Les modèles trouvés font 18 à 21 cm³, au-dessus de la cylindrée
  recommandée. Les petites cylindrées R290 inverter (10 à 14 cm³) existent
  chez GMCC, Highly, Landa et Rechi mais aucune fiche n'a été trouvée : à
  demander directement.
* **Prix unitaire autour de 100 à 150 $**, soit moins de 10 % du budget de
  1500 €. Le prix n'est pas une contrainte : il faut prendre le meilleur
  rendement disponible.
* Le bicylindre réduit vibrations et bruit (important pour une fenêtre) au
  prix d'un peu de rendement à basse vitesse.

## 5. Cahier des charges à envoyer aux fabricants

| Critère | Exigence |
|---|---|
| Fluide | R290, huile compatible (POE ou PAG), charge d'huile minimale (solubilité du propane, limite IEC 60335-2-40) |
| Type | rotatif hermétique BLDC (IPM), mono ou bicylindre |
| Cylindrée | 12 à 14 cm³ (16 cm³ maximum) |
| Vitesse | 10 à 15 tr/s minimum, 110 à 120 tr/s maximum |
| Rendement | η global ≥ 0,68 à PR 2,5 et 30 tr/s, ≥ 0,70 à PR 2,5 et 60 tr/s |
| Enveloppe | Te -25 à +15 °C, Tc 25 à 60 °C, refoulement ≥ 115 °C |
| Encombrement | hauteur ≤ 260 mm, masse ≤ 8 kg (à confirmer avec le dessin du boîtier) |
| Données à fournir | carte EN 12900 (polynômes 10 coefficients, débit massique et puissance électrique) à au moins 3 vitesses dont 20 à 30 tr/s ; conditions de référence ; rendement du variateur recommandé |
| Variateur | référence du variateur et de l'algorithme de commande (sans capteur, FOC) compatibles |

La carte reçue se branche directement :
`python simulateur.py --carte cartes/xxx.json` (voir README).

## 6. Étapes suivantes

1. Demander les cartes EN 12900 de 2 ou 3 compresseurs 12 à 16 cm³ (GMCC,
   Highly, Landa).
2. Les charger et refaire cette étude avec des données réelles.
3. Découpler la ventilation de la fréquence du compresseur et chercher le
   débit d'air optimal à chaque point.
4. Évaluer les options qui réduisent le travail de compression : surchauffe
   réduite (2 à 3 K avec EEV précis), pertes de charge de la vanne 4 voies,
   échangeur interne liquide / aspiration (peu utile avec R290, à vérifier).

## Sources

* [Area Cooling, GMCC EDTN210D32EFZ](https://areacooling.com/p/edtn210d32efz/)
* [Area Cooling, GMCC DSM180D19UDZ](https://areacooling.com/p/dsm180d19udz/)
* [Qishanr, GMCC DTN180D32UFZ](https://www.qishanrcompressor.com/products/r290-gmcc-rotary-compressor-dtn180d32ufz.html)
* [Qishanr (made-in-china), GMCC EDTN210D32EFZ](https://qishanr.en.made-in-china.com/product/uaDUlXGWaxcO/China-R290-Gmcc-Hermetic-DC-Inverter-Rotary-Compressor-Edtn210d32efz-for-Heat-Pump.html)
* [Qishanr (made-in-china), GMCC DTN210D32UFZ](https://qishanr.en.made-in-china.com/product/UJjrOEzGJtcZ/China-R290-China-Gmcc-DC-Inverter-Twin-Rotary-Air-Conditioner-Compressor-Dtn210d32ufz.html)
* [Qishanr, Highly PTL232SDN](https://qishanr.com/products/r290-highly-inverter-compressor-ptl232sdn)
* [OSTI, rendements mesurés d'un rotatif à vitesse variable et de son variateur](https://www.osti.gov/biblio/10175225)
