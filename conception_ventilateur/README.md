# Conception des ventilateurs de la PAC de fenêtre

But : les ventilateurs les plus sobres et les plus silencieux possible pour les deux batteries,
avec un moteur BLDC piloté en commande vectorielle (FOC) sans capteur.
Retour au [document principal](../README.md).

## Cahier des charges (repris de [`pac_9000btu.html`](../pac_9000btu.html))

| | Intérieur | Extérieur |
|---|---|---|
| Débit max | 800 m³/h | 2 500 m³/h |
| Perte de charge de la batterie | ≤ 25 Pa | ≤ 25 Pa (davantage quand elle givre) |
| Cas qui dimensionne | chauffage 8,3 °C | chauffage −8,3 °C (air dense : 1,33 kg/m³) |
| Budget actuel | 76 W au total, η = 0,30, **perte de sortie non comptée** | |
| Cible de ce dossier | η global 0,45–0,55 → ≈ 45–55 W au total | |

À COP 6, les ventilateurs à 76 W représentent 17 % de la puissance électrique ; les ramener à
40 W donne COP 6,5.

## Contenu

| Fichier | Rôle |
|---|---|
| `animation_ventilateur.html` | **ventilateur interactif** : vue animée, réglages (diamètre, pales, calage, vitesse, anneau, diffuseur, stator, motifs bio-inspirés, moteur), point de fonctionnement et bilan des pertes en direct ; modèle JS d'ordre de grandeur calé sur le W1G200 |
| `ventilateurs.html` | **page de synthèse** : recherches, figures, résultats, sources (regénérer : `.venv/bin/python conception_ventilateur/outils/fiche_ventilateurs.py`) |
| `outils/module_commun.py` | même batterie et même ventilateur des deux côtés : débits, vitesses et puissances par mode, baisse de Tc permise (sortie : `module_commun.json`) |
| `bibliographie_pales.md` | état de l'art : familles de ventilateurs, pales récentes, biomimétisme, BLDC / FOC, sources |
| `outils/predimensionnement.py` | poids dans le COP, perte de sortie, diamètre / vitesse / puissance, rendement d'un EC du commerce |
| `resultats_predimensionnement.md` | sortie du script (regénérer : `python3 conception_ventilateur/outils/predimensionnement.py > conception_ventilateur/resultats_predimensionnement.md`) |
| `articles/` | PDF des articles à lire |

Les courbes de ventilateurs réels utilisées par le simulateur restent dans `ventilateurs/`.

## Résultats

Ces chiffres reposent sur le cahier des charges (25 Pa par batterie), **pas encore sur le vrai
échangeur** : le module cylindrique ailetté n'a pas de courbe de perte de charge pour l'instant.

- **Extérieur : le diamètre décide de tout.** À 2 500 m³/h, un axial de 300 mm perd 75 Pa en
  énergie cinétique de sortie (trois fois la batterie) ; à 500 mm, 10 Pa. Le budget de 76 W de la
  fiche générale oublie cette perte de sortie.
- **Pale de départ** (hypothèse de travail, rien n'est dessiné) : axial Ø 500, moyeu 0,30, 3 pales
  larges en plaque cambrée, anneau tournant + labyrinthe, diffuseur, stator, bord de fuite dentelé.
- **Module commun** (même ventilateur et même échangeur des deux côtés) : 12 à 30 W de ventilation
  selon le mode ; la batterie intérieure surdimensionnée permet de baisser Tc (≈ −35 W net).
- Le ventilateur EC 200 mm du dépôt (ebm-papst W1G200) plafonne à η = 0,26 : l'hypothèse 0,30
  du cahier des charges est un bon produit standard, pas un objectif ambitieux.

Détail et sources : `ventilateurs.html` et les sections 5 à 9 de `bibliographie_pales.md`.

## Étapes suivantes

1. Obtenir la courbe Δp(débit) du module échangeur ailetté : elle décide du type de roue
   (≈ 25 Pa → axial ou tangentiel ; 50–100 Pa → centrifuge / blower).
2. Fixer le diamètre maximal disponible dans la fenêtre.
3. Puis dessiner la pale et la vérifier en CFD (section 10 de `bibliographie_pales.md`).
