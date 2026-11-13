# Compresseurs

**Document principal : [`etude_compresseurs.html`](etude_compresseurs.html)**, l'étude de marché des compresseurs R290
(11/11/2026). Elle est régénérée par `.venv/bin/python compresseurs/etude_marche.py`.

## Conclusions

* Aucun rotatif R290 de catalogue n'atteint vérifiablement η_is = 0,75 (rendement global, même définition que la fiche).
  Les meilleurs, recalculés au point ASHRAE, sont à 0,71–0,74 : Panasonic 7WD138Z, LG PST102MA, Panasonic 7SD110Z.
  Seul un prototype Highly optimisé pour ORNL mesure 0,77–0,80.
* Un compresseur de 10,8 cm³ capable de 128 tr/s n'existe pas : les vitesses maximales vont de 90 à 120 tr/s.
  Il faut viser 14–15 cm³, ce qui donne ≈ 95 tr/s à −15 °C.
* Courte liste :
  * Panasonic 7WD138Z ;
  * GMCC RDTN150D54TEZ3 / EDTN150D32EFZ ;
  * Highly PSD140RKQ-6B / Danfoss VRN150WSQASE (échantillon à l'unité).
* Avec η = 0,72, la machine rate de 1,5 à 2 % trois des quatre cibles de COP.

## Contenu

| Fichier | Rôle |
|---|---|
| `etude_compresseurs.html` | rapport (candidats, rendement, effet sur le COP, concurrents, réglementation, demandes à envoyer, toutes les sources) |
| `etude_marche.py` | générateur du rapport (données des candidats, recalcul CoolProp de η_is) |
| `sources/<famille>/` | copies des fiches, catalogues et articles, et `SOURCES.md` avec URL et date. Les PDF ne sont pas suivis par git (377 Mo) |
| `MODELE_carte.json`, `ajuster_carte.py` | gabarit de carte EN 12900 et outil d'ajustement, à remplir quand un fabricant envoie sa carte |
| `SYNTHETIQUE_generique.json` | modèle générique utilisé par le simulateur en attendant |
