# Conception des échangeurs de la PAC de fenêtre

But : des batteries air / propane qui donnent un COP 50 % au-dessus de Midea et Gradient,
dans le budget de charge de propane (152 g au total, IEC 60335-2-40).

Retour au [document principal](../README.md). Le cahier des charges chiffré (cibles, Te / Tc, hA requis,
surfaces, volume de propane, tubes) est la fiche de conception générale
**[`../pac_9000btu.html`](../pac_9000btu.html)**, à la racine du dépôt ; elle est régénérée par
`outils/analytique/fiche_pac_9000.py`.

Les scripts se lancent depuis la racine du dépôt (le `.venv` y est), par exemple :

```bash
.venv/bin/python conception_echangeur/outils/analytique/fiche_pac_9000.py
```

Ils calculent leurs chemins à partir de leur propre emplacement (`docs/`, `resultats_cfd/` et
`cfd_campagne/` sont relatifs à ce dossier).

## Contenu

| Emplacement | Contenu |
|---|---|
| `docs/resultats_cfd.pdf`, `docs/rapport_cfd.html` (+ `docs/rapport_cfd/`) | Synthèse et rapport des campagnes CFD |
| `docs/vue3d_ailettes.html` | Vue 3D interactive des cas d'ailettes |
| `docs/formes/<forme>/` | Résultats par forme simulée ; modèles CAO : cylindre Ø 100 (`cylindre_d100`, `cylindre_d100_t32`), cylindre Ø 150 × 400 à canal d'air hélicoïdal et 32 tubes en tournesol (`cylindre_d150_helice`, domaine air .step/.stl pour la CFD ; vue 3D `echangeur_d150.html` ; scripts `outils/cad/echangeur_d150.py`, `rendu_d150.py`, `html_d150.py`, `parametres_d150.json`) |
| `docs/maillages/`, `docs/figures/` | Vues des maillages, figures des notes |
| `docs/plan_formes_simples.md`, `docs/plan_echangeurs.md`, `docs/methode_optimisation.md` | Plans et décisions |
| `docs/criteres_module.md` | Cahier des charges du module et relation hA ↔ Δp (j, f/j, section libre) : critères de l'optimisation |
| `docs/resultats_niveau0.md` | Validation et convergence de la CFD |
| `docs/bibliographie_echangeurs.md`, `docs/biomimetisme.md` | Bibliographie commentée, pistes biomimétiques |
| `docs/pistes_et_idees.pdf` | Rapport des pistes |
| `docs/articles/` | Articles lus (non versionnés : droits d'éditeur) |
| `outils/analytique/` | Calculs sans CFD : cycle, charge, perte de charge propane et air (module Ø 100), figures ; `fiche_pac_9000.py` génère la fiche générale `../pac_9000btu.html` |
| `outils/cad/` | Modèles FreeCAD (cylindres Ø 100 et Ø 150, hélice, tournesol), rendus, fiches HTML |
| `outils/cfd_2d/`, `outils/cfd_3d/`, `outils/cfd_tpms/` | Chaînes OpenFOAM (formes 2D, ailettes et TPMS 3D) |
| `outils/aws/`, `outils/openfoam/` | Calcul sur AWS, installation d'OpenFOAM |
| `outils/balayage_gyroide.py` | Balayage de géométries gyroïdes avec le modèle du simulateur |
| `resultats_cfd/` | Archives des cas CFD (versionnées) |
| `cfd_campagne/` | Cas de calcul en cours (≈ 26 Go, non versionnés) |

Le simulateur de la PAC (`pac_fenetre/`, `simulateur.py`, `tests/`, `compresseurs/`) reste à la racine (voir [`../pac_fenetre/README.md`](../pac_fenetre/README.md)) ;
les corrélations CFD qu'il utilise sont écrites dans `pac_fenetre/donnees/` par `outils/cfd_tpms/ajuster.py`.
