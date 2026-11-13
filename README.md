# PAC de fenêtre réversible au propane (R290), 9 000 BTU/h

Pompe à chaleur air/air **réversible** (chauffage et clim) qui se pose dans une fenêtre d'appartement
(battant en Europe, guillotine aux USA), pour une pièce de 50 m² au plus, avec du **propane** comme
réfrigérant. Le but est d'être **50 % plus efficace** que les meilleures PAC de fenêtre du marché
(Midea PWHP 9k, Gradient All-Weather 120V).

C'est aujourd'hui une étude « sur papier » : calculs, simulation et CFD. Aucun prototype n'a été fabriqué.

**Fiche de conception générale : [`pac_9000btu.html`](pac_9000btu.html)**. Elle chiffre
toute la machine, de la cible de COP jusqu'au cahier des charges des échangeurs et des ventilateurs.
Elle est régénérée par `conception_echangeur/outils/analytique/fiche_pac_9000.py`.

## Objectifs

Capacité : 9 000 BTU/h = **2 638 W** à chaque point de certification US (AHRI / DOE).

| Point (COP ventilateurs inclus) | Meilleur du marché | **Cible (× 1,5)** |
|---|---|---|
| Clim 35 °C dehors | 3,99 | **5,98** |
| Chauffage 8,3 °C | 4,04 | **6,06** |
| Chauffage −8,3 °C | 2,60 | **3,90** |
| Chauffage −15 °C | 2,35 | **3,53** |

Autres objectifs : silencieux (la machine est près du lit), compacte (elle tient dans une fenêtre)
et même module échangeur + ventilateur côté pièce et côté extérieur.

## Contraintes dures

| Contrainte | Valeur | D'où elle vient |
|---|---|---|
| Charge de propane | ≤ 152 g au total, soit ≈ 56 g pour les deux échangeurs (≤ 276 cm³ chacun) | IEC 60335-2-40 (m1 = 4 × LFL) |
| Tenue à la pression | ≈ 25–30 bar, avec un coefficient de sécurité | propane à 40 °C de condensation et plus |
| Givre et condensat | évaporateur humide dans les deux modes ; givre sous ≈ 5 °C dehors | réversibilité, hiver |
| Compresseur | ≈ 10,8 cm³/tr, η_is ≥ 0,75 ; jusqu'à 128 tr/s à −15 °C | fiche de conception, étape 1 |
| Ventilateurs | ≤ 76 W au total (25 Pa par échangeur à η = 0,30) ; **à revoir** : la perte de sortie n'y est pas comptée | fiche de conception, étape 4 |

Le prix, le poids et la fabricabilité ne sont pas des contraintes : on considère que toutes les formes
sont imprimables (TPMS, tubes à forme libre…). L'épaisseur de paroi minimale et l'étanchéité restent,
elles, à tenir.

## Choix déjà faits

* **Module commun** : le même échangeur et le même ventilateur à l'intérieur et à l'extérieur. Le module
  est dimensionné sur le cas le plus dur, l'extérieur en clim (hA ≈ 1 100 W/K à 2 500 m³/h).
* **Échangeur** : un module cylindrique. Deux variantes sont à l'étude :
  * Ø 100 mm, 16 tubes de propane, conduits d'air tangentiels de 100 × 100 mm, ailettes encore à
    définir ;
  * Ø 150 × 400 mm, canal d'air hélicoïdal, 32 tubes disposés en tournesol.

  Les tubes sont verticaux pour drainer le condensat.
* **Ventilateurs** : moteur BLDC piloté en commande vectorielle (FOC) sans capteur. Le type de roue
  attend la courbe de perte de charge du module ailetté.
* **Compresseur** : rotatif BLDC R290 à vitesse variable.

## Limites de l'étude, à garder en tête

* Le COP cible suppose un compresseur haut de gamme (η_is = 0,75). Avec η_is = 0,65, aucune cible
  n'est tenue.
* En clim, la cible impose Te = 14 °C. À ce point, la machine ne déshumidifie plus ; un jour humide,
  la régulation baisse Te et le COP descend à ≈ 5,3.
* Seul le hA côté air est calculé : la résistance côté propane et celle de la paroi s'y ajoutent
  (prévoir 10 à 30 % de marge). Le givre n'est pas modélisé.
* La CFD 2D n'est fiable que jusqu'à Re ≈ 1 000 environ. Au-delà, elle donne des tendances à
  confirmer en 3D.
* Retour d'expérience UMD/DOE : un échangeur optimisé en CFD a perdu 10 % de COP sur un vrai
  climatiseur, à cause des ponts de condensat, de la distribution du réfrigérant et des collecteurs.
  Leur prototype imprimé en titane fuyait. Le régime sec ne suffit donc pas pour conclure.
* Le simulateur est quasi statique : il ne modélise ni la dynamique des batteries ni celle de la
  pièce.

## Les travaux

| Travail | Où | État | À lire en premier |
|---|---|---|---|
| **Conception générale** | racine | Cibles, cycle, Te / Tc, hA requis, budget de charge : faits | [`pac_9000btu.html`](pac_9000btu.html), [`docs/nomenclature.md`](docs/nomenclature.md) |
| **Simulateur physique** | [`pac_fenetre/`](pac_fenetre/README.md) | Fonctionne : cycle R290 temps réel, COP, givre, charge, aéraulique | [`pac_fenetre/README.md`](pac_fenetre/README.md) |
| **Échangeurs** | [`conception_echangeur/`](conception_echangeur/README.md) | Formes de tubes en CFD 2D et ailettes / TPMS en 3D : faites. Modules cylindriques Ø 100 (ailettes) et Ø 150 (hélice) : en cours | [`conception_echangeur/README.md`](conception_echangeur/README.md), `docs/resultats_cfd.pdf` |
| **Ventilateurs** | [`conception_ventilateur/`](conception_ventilateur/README.md) | Recherches, modèle de pale et module commun : faits. Choix de la roue : attend le Δp du module ailetté | [`conception_ventilateur/ventilateurs.html`](conception_ventilateur/ventilateurs.html) |
| **Compresseur** | [`compresseurs/`](compresseurs/README.md) | Étude de marché faite : aucun R290 de catalogue à η_is 0,75 vérifié (meilleurs ≈ 0,72–0,74) ; viser 14–15 cm³. Demandes de cartes à envoyer | [`compresseurs/etude_compresseurs.html`](compresseurs/etude_compresseurs.html) |
| Électronique, intégration fenêtre | — | Pas commencé (voir la nomenclature) | [`docs/nomenclature.md`](docs/nomenclature.md) |

## Organisation du dépôt

```
README.md                  ← ce document
pac_9000btu.html           ← fiche de conception générale (chiffres)
docs/                      nomenclature, captures du simulateur
conception_echangeur/      échangeurs : CFD, CAO, calculs, bibliographie
conception_ventilateur/    ventilateurs : pales, moteur, animation, bibliographie
pac_fenetre/               simulateur (code + README)
simulateur.py, tests/      lanceur et tests du simulateur
compresseurs/              étude de marché, sources, cartes constructeur (EN 12900) et outil d'ajustement
ventilateurs/              courbes constructeur des ventilateurs, lues par le simulateur
config_air/                circuits d'air (échangeur + accessoires) pour le simulateur
TODO_HUMAN.txt             tâches notées par Thomas
```

## Lancer

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python simulateur.py                                                  # simulateur (navigateur)
.venv/bin/python conception_echangeur/outils/analytique/fiche_pac_9000.py   # régénère pac_9000btu.html
```
