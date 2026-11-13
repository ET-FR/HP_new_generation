# Campagne CFD : corrélations j et f côté air des surfaces TPMS

But : remplacer la corrélation du gyroïde de Leeds (mesurée avec de l'eau, Pr ≈ 7) par des
corrélations **côté air** (Pr = 0,71) pour gyroïde, Diamond, Fischer-Koch S, I-WP et Primitive,
utilisées par le comparateur de l'onglet « Dimensionnement des échangeurs ».

## Principe

- **Domaine** : une cellule TPMS en section (périodique en y et z, patchs `cyclicAMI`), la
  **profondeur réelle** du noyau dans le sens de l'air (24 mm par défaut), un tampon libre
  en amont et en aval.
- **Géométrie** : le solide est la région F < niveau, entre x = 0 et x = D. Côté air, une
  batterie « feuillet » (paroi + propane) et une batterie « hybride » (structure pleine,
  propane dans des tubes) ont la même géométrie : une seule campagne sert aux deux.
- **Comparaison à Dh égal** (4 mm par défaut) et à porosité égale (0,6) : à Dh et φ égaux,
  toutes les surfaces ont la même surface volumique (4 φ / Dh). Seuls j et f les distinguent.
- **Physique** : air incompressible à 20 °C, paroi isotherme (propane diphasique, paroi
  mince), température transportée comme scalaire passif. Laminaire jusqu'à Re = 300,
  k-ω SST au-delà (comme Qureshi, Leeds).
- **Sorties** : NTU à partir de la température de mélange en sortie, puis j de Colburn ;
  f **apparent** (entrée, sortie et zone d'établissement comprises) à partir de Δp.
  Au-delà de Re ≈ 150, l'écoulement oscille légèrement : les grandeurs sont moyennées sur
  le dernier quart des itérations et la fluctuation est indiquée.

## Utilisation

```bash
source /usr/lib/openfoam/openfoam2412/etc/bashrc
cd ~/Documents/PROJETCS/HP_new_generation

# 1. Campagne : 5 surfaces × 5 Re (reprise automatique si interrompue)
.venv/bin/python outils/cfd_tpms/lancer_campagne.py --dossier cfd_campagne \
    --surfaces gyroide diamond fks iwp primitive --Re 100 200 400 800 1600 \
    --finesse 8 --raffinement 2 --nproc 4 --paralleles 2

# 2. Ajustement des corrélations -> pac_fenetre/donnees/correlations_air_tpms.json
.venv/bin/python outils/cfd_tpms/ajuster.py cfd_campagne/resultats.csv
```

Puis relancer le serveur du simulateur : le comparateur utilise automatiquement les
nouvelles corrélations, et les lignes « à calibrer » deviennent calculables.

Un cas isolé :

```bash
.venv/bin/python outils/cfd_tpms/creer_cas.py --surface fks --Re 400 --dossier cas/fks_400
bash cas/fks_400/Allrun
.venv/bin/python outils/cfd_tpms/extraire.py cas/fks_400
```

## Fichiers

| Fichier | Rôle |
|---|---|
| `creer_cas.py` | Génère STL (marching tetrahedra) + cas OpenFOAM complet + `Allrun` |
| `lancer_campagne.py` | Plan surfaces × Re, exécution en parallèle, reprise |
| `extraire.py` | Lit `postProcessing`, calcule NTU, j, f, h ; écrit `resultats.csv` |
| `ajuster.py` | Lois j = a·Re^-b et f = c·Re^-d par surface, JSON pour le simulateur |
| `pac_fenetre/tpms.py` | Fonctions implicites et géométrie des 5 surfaces (partagé avec le simulateur) |

## Réglages du maillage

`--finesse` = mailles de base par Dh, `--raffinement` = niveaux snappyHexMesh à la paroi.
Voir l'étude de convergence dans `docs/` avant de changer les valeurs par défaut.

## Limites

- Paroi isotherme et lisse : la rugosité d'impression (LPBF) augmente f et un peu j, à
  vérifier par un essai en soufflerie sur un échantillon imprimé.
- Pas de condensation ni de givre (régime sec).
- f apparent valable pour des profondeurs proches de celle de la campagne.
