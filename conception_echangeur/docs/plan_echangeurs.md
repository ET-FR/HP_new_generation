# Plan : choisir et concevoir les batteries de la PAC de fenêtre R290

Établi le 8 novembre 2026, à partir des lectures résumées dans `bibliographie_echangeurs.md`.

## Objectif

Des batteries intérieure et extérieure qui donnent le **COP (et le SCOP) le plus élevé possible** dans
l'enveloppe d'une fenêtre, avec **≤ 152 g de propane**, en PAC **réversible** (chaque batterie est
évaporateur humide dans un mode, et la batterie extérieure givre en chauffage).
Hypothèse de travail : toutes les formes sont fabricables (impression 3D) ; restent les limites
physiques (pression, charge, paroi minimale, givre, bruit).

## Pistes retenues

1. **Tubes nus profilés** (1-3 mm, sans ailettes), en **géométrie variable** à plusieurs passes à
   contre-courant, **collecteurs intégrés**, **tubes verticaux**. Piste n° 1.
2. **TPMS hybride** (Diamond ou Fischer-Koch S côté air, tubes côté propane). Concurrent jusqu'à la
   fin de la phase 1.
3. Référence à battre : tube-ailettes du simulateur (et microcanaux).

Pistes notées en cours d'étude (tubes parallèles à l'air, distributeur à orifices calibrés,
collecteurs en arbre de Murray, biomimétisme) : voir `docs/plan_formes_simples.md`, section 10,
et `docs/biomimetisme.md`.

## Phase 0 : fondations (en cours)

| Tâche | État |
|---|---|
| Chaîne CFD OpenFOAM (`outils/cfd_tpms`) : génération, calcul, extraction j/f, ajustement | fait |
| Convergence en maillage (gyroïde, Re 200) : 8 mailles/Dh + raffinement 2 suffisent (écart < 0,5 % avec 292 k cellules) | **fait** |
| Comparateur de surfaces dans l'onglet Dimensionnement | fait |
| **Commiter tout le travail de la session** (rien n'est commité) | à faire en premier |

## Phase 1 : comparaison juste tubes profilés / TPMS (≈ 1 à 2 semaines)

But : comparer les familles **avec les mêmes définitions de j et f et les mêmes conditions**.

1. **CFD 2D de faisceaux de tubes** (`outils/cfd_2d`, chaîne OpenFOAM propre aux formes 2D) : tubes ronds,
   elliptiques, lentille type NTHX1, goutte d'eau ; quinconce, périodique en hauteur, paroi isotherme.
   - Validation : tubes ronds contre VDI (Gnielinski / Gaddis) ; NTHX1 contre la thèse de Klein
     (tableau 73 : j = 0,024, f = 0,060, j/f = 0,40 à 3 m/s).
2. **Campagne TPMS 3D** : gyroïde, Diamond, FKS (+ I-WP, Primitive) × Re 100-1 600, φ = 0,6 ;
   environ 25 cas × 15-30 min, en une nuit dans `cfd_campagne/`.
3. **Comparaison commune** : j, f, j/f et puissance de ventilation par unité d'échange, puis
   **COP du cycle complet** dans le comparateur (corrélations ajustées branchées automatiquement).

**Décision G1** : garder 1 ou 2 familles pour l'optimisation.

## Phase 2 : compléter le modèle de la machine (en parallèle de la phase 1, sans CFD)

| Tâche | Pourquoi |
|---|---|
| Volume des **collecteurs** dans la charge | les collecteurs ont annulé une partie des gains de charge à l'UMD |
| **Pénalité humide** (Δp × 2 à 2,5 sur tubes nus fins, nombre de Lewis) | cause n° 1 de l'échec des essais réels |
| **Givre et dégivrage** par technologie (temps de givrage, rétention d'eau, énergie de dégivrage) | inconnu majeur pour une PAC |
| Contrainte **T1 / T3 du bon côté de l'air entrant** | défaut du modèle actuel (croisements non physiques) |
| **Côté réfrigérant des petits canaux** : Shah 2016 (h condensation), Xu-Fang 2013 (Δp), Churchill, fraction de vide Ali-Sadatomi-Kawaji | indispensable sous 3 mm |
| **Bruit** : vitesse frontale et ventilateur | critère majeur pour un appareil dans la pièce |
| **SCOP** (EN 14825) comme objectif principal | la machine fonctionne surtout à charge partielle |

## Phase 3 : optimisation (≈ 3 à 4 semaines)

Méthode de l'UMD (optimisation assistée par métamodèle), avec **nos objectifs** :
1. Plan d'expériences de **tubes NURBS 2D** (500 à 1 000 cas, 1 à 2 nuits).
2. **Métamodèle** par krigeage (h, Δp côté air).
3. **NSGA-II** sur le cycle complet, les deux batteries et les deux modes :
   - objectifs : **max SCOP (ou COP)**, **min charge** ;
   - contraintes : enveloppe de la fenêtre, charge ≤ 152 g, tenue à la pression (paroi), bruit ;
   - variables : forme, taille, pas, rangs, passes et géométrie par passe.
4. Affinage local éventuel par **méthode adjointe** (Klein : encore −40 à −50 % de Δp).
5. Même démarche pour le **TPMS hybride** s'il est toujours en lice (cellule graduée, collecteurs intégrés).

**Décision G2** : choix d'un design de batterie intérieure et extérieure.

## Phase 4 : validation physique

1. **Échantillon imprimé** (≈ 100 × 100 mm), métal (AlSi10Mg / AlSi7Mg, polissage chimique) :
   j et f en soufflerie, en sec puis en humide ; **essai de givrage** en chambre froide ;
   **essai d'éclatement** (propane ≈ 25-30 bar, avec coefficient de sécurité).
2. **Batterie complète** avec collecteurs intégrés, tubes verticaux.
3. **Essai système** dans une unité de fenêtre, comparé à Gradient / Midea.

## Lectures en parallèle (par ordre de priorité)

1. Étude terrain **ACEEE** (Gradient, Midea) : COP réels de la concurrence, objectifs chiffrés.
2. Revue **ORNL** sur le dégivrage ; givre microcanaux vs tube-ailettes.
3. **Thèse de Tancabel** (2022) : côté tube, mécanique, humide.
4. **Bacellar 2014** : corrélations CFD côté air pour tubes fins (validation de la phase 1).

## Risques principaux

| Risque | Parade |
|---|---|
| Ponts de condensat, givre sur tubes fins serrés | tubes verticaux, pas minimal, revêtements, essai de givrage tôt (phase 4.1) |
| Mauvaise distribution du réfrigérant | collecteurs intégrés conçus avec la batterie, essai dès le premier prototype |
| Étanchéité des pièces imprimées | paroi suffisante, polissage, essai d'éclatement précoce |
| Corrélations CFD en paroi lisse | rugosité mesurée sur l'échantillon imprimé |
| Réversibilité (sens du réfrigérant inversé) | optimiser les deux modes ensemble, pas un condenseur seul |
