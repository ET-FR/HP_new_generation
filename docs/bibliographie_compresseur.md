# Bibliographie : compresseurs rotatifs à vitesse variable

But : documenter comment les pertes d'un rotatif (fuites, réchauffement à
l'aspiration, espace mort, moteur) varient avec la vitesse, pour améliorer le
modèle de compresseur du simulateur (`pac_fenetre/physique.py`,
`PompeAChaleur.compresseur`). Voir aussi [`compresseur.md`](compresseur.md).

Accès : les archives de Purdue, CORE et Wiley renvoient une page anti-robot
dans cette session ; seuls les résumés et extraits des moteurs de recherche
ont été lus pour ces articles. L'article arXiv a été lu en entier.

## 1. Article lu en entier

**Zheng, Zhao, Lyu, Gao et al. (Université de Pékin et centre de recherche
Midea), « Performance analysis for a rotary compressor at high speed:
experimental study and mathematical modeling », arXiv 2407.11080, 2024.**
[PDF](https://arxiv.org/pdf/2407.11080)

* Rotatif hermétique monocylindre, **R32**, banc calorimétrique Midea avec
  capteurs de pression rapides dans le cylindre (diagramme P-V) et mesure du
  déplacement de la palette et du clapet.
* Conditions : évaporation -14,3 °C, condensation 33,3 °C (0,5 et 2,1 MPa,
  taux de compression 4,2), vitesses de 80 à 200 tr/s.
* Rendement décomposé en η = η_v · η_c · η_f · η_m (volumétrique, processus
  dans le cylindre, mécanique, moteur).

Résultats mesurés :

| Grandeur | Valeur | Variation avec la vitesse |
|---|---|---|
| Rendement global η | environ 68 % au maximum (160 tr/s) | baisse lente de 80 à 140 tr/s, chute nette à 200 tr/s |
| Rendement volumétrique η_v | 84 % à 80 tr/s, jusqu'à 105 % à 180 tr/s | monte avec la vitesse (effet de suralimentation par les ondes de pression dans le tube d'aspiration) |
| Moteur et frottements η_m · η_f | minimum 83 % à 140 tr/s, 87 % à 200 tr/s | |
| Perte par fuites | jusqu'à 15 % du débit | **première cause de perte** sur toute la plage |
| Perte par réchauffement à l'aspiration | environ 10 % (14 % à 200 tr/s) | presque constante sous 140 tr/s |
| Perte par espace mort | environ 3 % | constante (géométrie) |
| Retour de gaz par le clapet | négligeable | |
| Perte au refoulement (surcompression, inertie du clapet) | deuxième cause de perte | augmente avec la vitesse |

Conclusions utiles pour nous :

1. **Les fuites sont la première perte** d'un rotatif. Leur réduction passe
   par les jeux internes (fabrication, concentricité).
2. **Le réchauffement du gaz aspiré coûte environ 10 % de débit**, presque
   indépendamment de la vitesse. Notre modèle ne le représente pas comme un
   terme séparé.
3. **L'espace mort coûte environ 3 %** à taux de compression 4,2. Notre
   `espace_mort = 0,04` donne 6 % à taux 2,8 : probablement surestimé, mais
   compensé par l'absence de terme de réchauffement (notre η_v total de 0,91
   est cohérent avec les 0,90 recalculés sur les données GMCC).
4. Au-dessus de 140 tr/s, les ondes de pression à l'aspiration et l'inertie
   du clapet dégradent le rendement. Ce n'est pas notre plage d'usage
   (15 à 110 tr/s).

## 2. Articles repérés, à lire (résumés seulement)

### Pertes en fonction de la vitesse

* **Rotatif à vitesse variable alimenté par convertisseur de fréquence**,
  conférence de Purdue sur les compresseurs (ICEC), article 2026.
  [Lien](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=2026&context=icec).
  D'après le résumé : **les fuites dominent les pertes à basse vitesse**, la
  re-détente du gaz comprimé à haute vitesse ; le meilleur rendement est vers
  5500 à 6500 tr/min (92 à 108 tr/s). C'est l'article le plus utile pour
  notre plage de 15 à 60 tr/s.
* **« Rolling Piston Type Rotary Compressor Performance Analysis »**, ICEC,
  article 1385. [Lien](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=1385&context=icec).
  Rendement maximal d'environ 72 à 74 % sur un ancien rotatif de 3/4 ch.
* **Laboratoire, rotatif à vitesse variable et son variateur** (OSTI).
  [Lien](https://www.osti.gov/biblio/10175225). À 30 Hz, un écart de 5 % sur
  la tension du variateur fait perdre environ 5 % de rendement
  isentropique : le réglage du variateur compte à basse vitesse.

### Fuites (jeux internes)

* **« Comprehensive Analysis of Leakage in Rotary Compressors »**, ICEC,
  article 2120. [Lien](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=2120&context=icec).
  Sept chemins de fuite modélisés et comparés à des mesures.
* **Kim et al., fuite par le jeu radial rouleau / cylindre**, ICEC 2016,
  article 2493. [Lien](https://docs.lib.purdue.edu/icec/2493),
  [PDF CORE](https://core.ac.uk/download/77954903.pdf). Coefficients de débit
  tirés d'essais et de CFD, simulation validée sur mesures calorimétriques.
* **Yanagisawa et Shimizu, « Leakage losses with a rolling piston type rotary
  compressor »**, International Journal of Refrigeration, 1985.
  [Lien](https://www.sciencedirect.com/science/article/abs/pii/0140700785901550).
  Référence classique : jeu radial modélisé comme une tuyère suivie d'un
  canal avec frottement.

### Spécifique au propane (R290)

* **Fuites du R290 dans un rotatif, comparées au R22 et au R410A**,
  International Journal of Refrigeration, 2015.
  [Lien](https://www.sciencedirect.com/science/article/abs/pii/S014070071500033X).
* **Rotatif R290 sans huile : nouvelle structure, fuites et performances**,
  International Journal of Refrigeration, 2014.
  [Lien](https://www.sciencedirect.com/science/article/abs/pii/S0140700714002680).
  La structure proposée limite la perte de rendement volumétrique due aux
  fuites à environ 8 %.
* **Fuites du R290 dans un rotatif, prédiction du débit avec solubilité et
  viscosité de l'huile**, ICEC, article 3838.
  [Lien](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=3838&context=icec).
  Le rendement volumétrique est prédit à partir d'un seul point d'essai de
  référence et des données de solubilité et de viscosité : utile pour
  extrapoler un point catalogue (comme SEER60) à d'autres conditions.
* **Rotatif R290 à très haute vitesse**, International Journal of
  Refrigeration, 2024.
  [Lien](https://www.sciencedirect.com/science/article/abs/pii/S0140700724002111).
* **R290 contre R32 dans des rotatifs de même cylindrée**, Applied Thermal
  Engineering, 2024 (mesures et simulations 0-D et 3-D).
  [Lien](https://www.sciencedirect.com/science/article/abs/pii/S1359431124021598).
  Le R290 a un meilleur rendement volumétrique et, aux vitesses courantes, un
  meilleur rendement isentropique.
* **Schnabel et al., cycles R290 à charge réduite**, Chemie Ingenieur Technik,
  2023. [Lien](https://onlinelibrary.wiley.com/doi/full/10.1002/cite.202200150).
  Cartes de performance mesurées d'un compresseur R290 de 20 à 120 tr/s,
  rendements volumétrique et isentropique déduits.
* **Comparaison scroll et rotatif pour les PAC américaines**, ICEC,
  article 3663.
  [Lien](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=3663&context=icec).

### Synthèse générale

* **Aw et Ooi, « A Review on Sliding Vane and Rolling Piston Compressors »**,
  Machines 9 (2021) 125.
  [PDF](https://pdfs.semanticscholar.org/a2a7/080d1ef8d26ff04ba1e7525e22c0d6082934.pdf).
  Note notamment que la forte solubilité du R290 dans l'huile PAG augmente
  les fuites.
* **CIBSE Journal, module 163 : rotatifs à rouleau pour la climatisation**
  (Toshiba). [Lien](https://www.cibsejournal.com/cpd/modules/2020-06-toshiba/).

## 3. Ce que cela change pour le modèle du simulateur

Le modèle actuel regroupe les pertes en trois termes (η_v avec espace mort et
fuites, η_is fonction du taux et de la vitesse, η_mot fonction de la
vitesse). La littérature suggère de les séparer :

| Terme | Forme proposée | Calage |
|---|---|---|
| Fuites | débit de fuite à peu près indépendant de la vitesse, donc perte relative ∝ 1 / f, croissante avec le taux de compression | ICEC 2026, 2120, 3838 ; point SEER60 GMCC |
| Réchauffement à l'aspiration | environ 10 % du débit, presque constant | arXiv 2407.11080 |
| Espace mort | environ 3 % à taux 4,2, selon la loi polytropique | arXiv 2407.11080 |
| Refoulement (clapet) | croissant avec la vitesse, faible sous 100 tr/s | arXiv 2407.11080 |
| Moteur, frottements, variateur | 83 à 87 % ensemble ; variateur mal réglé : -5 % à 30 Hz | arXiv 2407.11080, OSTI |

Le point de rendement le plus important pour l'objectif (basse vitesse, 20 à
30 tr/s) est justement celui où les fuites dominent et où les données
publiées sont les plus rares. Seules les cartes constructeur à plusieurs
vitesses permettront de le caler.
