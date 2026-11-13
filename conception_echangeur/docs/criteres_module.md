# Critères physiques pour optimiser le module échangeur

Note du 11 novembre 2026. Elle fixe ce que l'optimisation doit maximiser et les limites à
respecter. Les chiffres viennent de la fiche de conception générale
([`../../pac_9000btu.html`](../../pac_9000btu.html)). Le choix de l'algorithme est dans
[`methode_optimisation.md`](methode_optimisation.md).

## 1. Cahier des charges du module

Le même module (échangeur + ventilateur) est monté côté pièce et côté extérieur. Il est donc
dimensionné sur le cas le plus dur des deux côtés : **l'extérieur en clim** (3 000 W à rejeter
dans de l'air à 35 °C, condensation à 40 °C).

| Exigence | Valeur |
|---|---|
| hA côté air | **≥ 1 104 W/K à 2 500 m³/h**, plus 10 à 30 % de marge (paroi et côté propane) |
| Perte de charge air | **≤ 25 Pa à 2 500 m³/h** |
| Volume intérieur de propane | ≤ 276 cm³ par échangeur (152 g pour toute la machine, IEC 60335-2-40) |
| Perte de charge propane | ≤ 0,5 K de température de saturation |
| Eau | Évacuation du condensat et du givre (tubes verticaux) |
| Pression | Tenue à ≈ 25–30 bar, avec un coefficient de sécurité |

Côté pièce, le même module suffit avec moins d'air : environ 830 m³/h en chauffage et
570 m³/h en clim. Il faut vérifier le hA **aux deux débits** par calcul ou en CFD, car la loi
hA ∝ débit^0,6 utilisée ici n'est pas garantie pour une géométrie nouvelle.

### Pour mémoire : échangeur intérieur seul (s'il était différent de l'extérieur)

Le chauffage dimensionne : 2 638 W, air à 21,1 °C, condensation à 32 °C.

| Débit m³/h | Air sortie °C | ε | NTU | hA requis W/K |
|---|---|---|---|---|
| 720 | 32,0 | 1,00 | ∞ | ∞ (limite absolue : l'air ne peut pas dépasser Tc) |
| 750 | 31,6 | 0,96 | 3,24 | 816 |
| **800** | **30,9** | **0,90** | **2,31** | **619** |
| 1 000 | 29,0 | 0,72 | 1,28 | 428 |
| 1 200 | 27,6 | 0,60 | 0,92 | 370 |

Relâcher la contrainte en montant Tc coûte cher : 2 K de plus font perdre ≈ 6 % de COP.

## 2. Relation entre hA et perte de charge

Notations : u est la vitesse dans la section libre A_c, ρ la masse volumique, G = ρu, A la
surface d'échange, Pr ≈ 0,71 pour l'air.

    h   = j · G · cp · Pr^(-2/3)           (j : Colburn)
    Δp  = f · (A / A_c) · ρu²/2           (f : Fanning ; pertes d'entrée et de sortie négligées)
    NTU = j · (A / A_c) · Pr^(-2/3)

On en tire :

    Δp = (f / j) · NTU · Pr^(2/3) · ρu²/2          (Pr^(2/3) ≈ 0,80)

Le NTU est imposé par le cahier des charges. Il reste deux leviers :
- **f/j, la qualité de la forme** : c'est le seul terme sur lequel le dessin agit ;
- **la vitesse dans l'échangeur**, qui pèse en u².

**Limite physique (analogie de Reynolds / Chilton-Colburn).** Pour une plaque lisse, j ≈ f/2,
donc f/j ≈ 2 au mieux. La traînée de forme (sillages derrière les obstacles) ajoute de la
perte de charge sans ajouter d'échange.

| Surface | f/j typique |
|---|---|
| Plaque lisse (idéal) | ≈ 2 |
| Tubes profilés à forme optimisée (UMD) | ≈ 2 – 2,5 |
| Ailettes plates, persiennes | ≈ 3 – 5 |
| Faisceau de tubes ronds | ≈ 5 – 10 |
| Notre gyroïde (CFD, j/f ≈ 0,08) | ≈ 12 |

Les définitions de f diffèrent selon les sources : il faut les harmoniser avant de comparer.

**Pour une géométrie fixée, quand seule la vitesse change :**
- h ∝ u^0,5–0,8 ;
- Δp ∝ u^1,7–2 ;
- puissance du ventilateur ∝ u^2,7–3.

Doubler la vitesse donne environ × 1,5 sur hA, × 3,5 sur Δp et × 7 sur la puissance du
ventilateur. La règle est donc : **grande section, air lent, surface à faible f/j**.

## 3. Conséquence directe : la section libre minimale

Cas du module à 2 500 m³/h, avec NTU = 1,37 et Δp ≤ 25 Pa :

| f/j | ρu²/2 admis | u max | Section libre minimale A_c |
|---|---|---|---|
| 2 | 11,5 Pa | 4,5 m/s | 0,15 m² |
| 4 | 5,7 Pa | 3,2 m/s | 0,22 m² |
| 10 | 2,3 Pa | 2,0 m/s | 0,34 m² |

Un conduit tangentiel de 100 × 100 mm fait 0,01 m², soit environ 20 fois trop peu pour un
seul module. Il faut plusieurs modules en parallèle, ou un passage d'air bien plus large que
le conduit d'entrée.

## 4. Ce que l'optimisation doit en retenir

- **Objectif :** maximiser le hA (ou le NTU) à Δp, volume de propane et encombrement donnés.
  De façon équivalente, minimiser f/j à j suffisant.
- **Contraintes à vérifier en premier**, car elles éliminent le plus de géométries :
  1. la section libre A_c ;
  2. le volume de propane.
- **Comparer les surfaces** par j et f/j au même Reynolds, avec les mêmes définitions.
- **Ne pas conclure sur le seul régime sec.** Le condensat et le givre augmentent Δp
  (essai UMD : × 2,3 à 2,5 en humide).
- Les « 19 W » de ventilateur de la fiche ne sont pas une caractéristique de l'échangeur.
  Ils viennent de l'hypothèse 25 Pa et η = 0,30. Le dossier ventilateurs montre que la perte
  de sortie s'y ajoute.
