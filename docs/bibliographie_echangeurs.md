# Bibliographie : surfaces d'échange côté air pour la batterie air / propane

Recherche du 5 novembre 2026. Seuls les résumés et pages de synthèse ont été lus : les
chiffres sont ceux annoncés par les auteurs, dans leurs conditions (fluide, Re), à vérifier
dans les articles complets avant toute décision.

Contexte d'utilisation : batterie air / R290 d'une PAC de fenêtre. Le côté air limite
l'échange (~95 % de la résistance thermique dans notre modèle), on vise peu de puissance
ventilateur, une charge de propane ≤ 152 g et un évaporateur qui givre.

## 1. Surfaces TPMS (gyroïde, Diamond, Primitive, FKS, FRD, I-WP)

| Réf. | Apport | Limite |
|---|---|---|
| [Gyroid / Diamond / Primitive, 2026](https://yznkxjs.xml-journal.net/en/article/doi/10.7538/yzk.2026.youxian.0041) | f de Fanning : gyroïde < Diamond < Primitive. Diamond : meilleure synergie de champ. Primitive : faible Δp mais échange faible. | Fluide non précisé dans le résumé. |
| [Six TPMS comparés (JAFM)](https://www.jafmonline.net/article_2898.html) | Classement thermo-hydraulique global : Diamond 1er, FKS 2e, I-WP 3e, FRD 5e. FRD : meilleur échange mais Δp très élevée. | |
| [FKS, Gyroid, Diamond, SplitP (E3S 2024)](https://www.e3s-conferences.org/10.1051/e3sconf/202456001009) | FKS : meilleur Nusselt ; Δp importante aux Re élevés. | |
| [Revue TPMS (encyclopedia.pub)](https://encyclopedia.pub/entry/download_pdf/cc8f1e96f870c24be123fd472c1879b8) | Structures FK : +23 à +356 % d'échange à Δp similaire vs Schwarz-D. Primitive (feuillet) : le plus faible. | Revue, conditions hétérogènes. |
| [Revue TPMS 2026 (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S073519332600641X) | Gyroïde > ailettes droites en laminaire (échange volumique). | Essais surtout liquide-liquide. |
| [Mesures côté air, TPMS imprimés (IJHMT 2023)](https://www.sciencedirect.com/science/article/pii/S0017931023004167) | Mesure directe côté air : gyroïde +13 % de Nusselt à puissance de pompage égale vs tube droit. | Seule mesure côté air trouvée : gain modeste. |
| [Thèse UMD, caractérisation TPMS](https://drum.lib.umd.edu/handle/1903/28493) | Caractérisation et validation thermo-hydraulique d'échangeurs TPMS. | À lire. |
| [TPMS hybrides et uniformes (Waterloo)](https://openjournals.uwaterloo.ca/index.php/hi-am/article/view/6777) | TPMS hybrides / gradués. | À lire. |
| [Précooler TPMS, air / azote (2026)](https://www.sciencedirect.com/science/article/abs/pii/S0735193326016350) | Diamond, Gyroid, SplitP : Δp air +70 à +80 %. | Grand écart de température, cryogénie. |

Corrélations disponibles dans le code : gyroïde uniquement, Qureshi (Leeds, 2026), eau (Pr ≈ 7).

## 2. Hybride : TPMS côté air, tubes / canaux côté fluide

| Réf. | Apport | Limite |
|---|---|---|
| [Gyroid-pipe, aviation à pile à combustible (Eng. Proc. 2026)](https://doi.org/10.3390/engproc2026133078) | Gyroïde côté air avec canaux de refroidissement intégrés, essais. Sections air plus épaisses → courbures plus douces → moins de Δp. | Côté fluide : eau, pas réfrigérant. |
| [Gyroid-tpms à canaux intégrés (Research Square)](https://www.researchsquare.com/article/rs-9416182/v1) | Surface d'échange ×3,12 et Δp −3 % vs référence. | Préprint. |

Intérêt pour nous : garder un petit volume côté propane (charge) tout en profitant de la surface TPMS côté air.

## 3. Tubes nus fins / à forme optimisée (Université du Maryland, programme DOE)

| Réf. | Apport | Limite |
|---|---|---|
| [Rapport final DOE (OSTI 2293536)](https://www.osti.gov/biblio/2293536) | Batteries air / réfrigérant à tubes non ronds optimisés : > +20 % de performance, −20 % de taille, −25 % de charge. 10 prototypes, dont fabrication additive. | Chiffres de l'équipe. |
| [Page projet DOE](https://www.energy.gov/eere/buildings/articles/design-and-manufacturing-high-performance-reduced-charge-heat-exchangers) | Objectifs : −25 % taille, −25 % masse, −30 % charge. | |
| [Thèse UMD, tubes nus optimisés](https://drum.lib.umd.edu/bitstreams/77b1f03d-5310-4635-86ad-f6e35a55b819/download) | −40 à −50 % de Δp air à échange au moins égal vs tube rond nu, en sec et en humide ; essai système en climatiseur. | À confirmer dans le texte complet. |
| [Présentation DOE 2016](https://www.energy.gov/sites/default/files/2016/04/f30/312103_Radermacher_040616-1505.pdf) | Tubes nus 0,5 et 0,8 mm. Ponts de condensat en humide → Δp ↑, revêtements nécessaires. | |
| [Miniaturized air-to-refrigerant HX (OSTI 1358252)](https://www.osti.gov/biblio/1358252) | Échangeurs air / réfrigérant miniaturisés. | À lire. |

Auteurs clés : Bacellar, Aute, Radermacher (corrélations CFD côté air pour tubes fins avec et sans ailettes).

## 4. Ailettes classiques (référence à battre)

| Réf. | Apport |
|---|---|
| [DeJong et Jacobi, persiennées vs offset strip (Illinois)](https://www.ideals.illinois.edu/items/11166) | Persiennées : moins de surface pour un même échange, mais puissance de pompage nettement plus élevée. Offset strip préférable si l'efficacité compte plus que la taille. |
| [Plain / wavy / louver en humide (KFUPM)](https://pure.kfupm.edu.sa/en/publications/comparative-analysis-of-airside-thermalhydraulic-behavior-of-plai/) | Ondulées : intermédiaires (échange et frottement). |
| [Ailettes ondulées perforées, winglets (Cardiff)](https://orca.cardiff.ac.uk/152008/1/energies-15-05904.pdf) | PEC max 1,24 ; paires de winglets sur ailettes ondulées. |
| [Comparaison tubes plats (scientific.net)](https://www.scientific.net/AMR.354-355.389) | Offset strip : meilleure intensification parmi plain, wavy, louvered, offset strip. |

## 5. Mousses métalliques

| Réf. | Apport | Limite |
|---|---|---|
| [Illinois, mousses vs persiennées](https://www.ideals.illinois.edu/items/29665) | h ×2 à ×3 vs persiennées ; meilleur drainage. | Δp élevée. |
| [Nawaz et Jacobi 2018 : sec, humide, givrage (OSTI)](https://www.osti.gov/biblio/1474467) | Comportement sec / humide / givrage. | Résultats givrage non vérifiés. |
| [Purdue 2012, drainage](https://docs.lib.purdue.edu/iracc/1312) | Essais de drainage. | |

## 6. Ailettes imprimées et optimisation topologique

| Réf. | Apport |
|---|---|
| [Unger et al., picots intégrés (HZDR)](https://www.fzd.de/publications/Publ-30842) | Picots dentelés (SIPF) : meilleur Nusselt, frottement modéré, Re < 5 000. |
| [Picots en sablier (IIR)](https://iifiir.org/en/fridoc/34036) | Moins de matière, plus de section libre, moins de Δp. |
| [Picots bio-inspirés auto-organisés (CityU)](https://scholars.cityu.edu.hk/en/publications/a-bioinspired-programmable-self-organization-approach-for-designi/) | Jusqu'à +60 % de Nusselt (dissipateurs). |
| [Optimisation topologique côté air (core.ac.uk)](https://core.ac.uk/download/84004481.pdf) | Conductance maximale à Δp imposée, surfaces imprimées. |
| [Optimisation voxel 3D (NASA)](https://ntrs.nasa.gov/api/citations/20210024939/downloads/VoxelBased3DOptimization_BashirMekki_Final.pdf) | Méthode d'optimisation 3D. |
| [Modèle d'écoulement établi pour l'optimisation topologique (DTU)](https://orbit.dtu.dk/en/publications/a-fully-developed-flow-thermofluid-model-for-topology-optimizatio/) | Méthode. |

## Points ouverts

- Givrage et drainage très peu documentés pour TPMS, mousses et tubes fins : risque n° 1 pour la batterie extérieure.
- Aucune corrélation j / f côté air (Pr ≈ 0,7) trouvée pour Diamond, FKS, I-WP : à produire par CFD sur cellule périodique.

## 7. Lecture détaillée : rapport final UMD / DOE DE-EE0008221 (`docs/DE-EE0008221 University of Maryland, College Park.pdf`)

« Design and Manufacturing of High Performance, Reduced Charge Heat Exchangers », Université du
Maryland (Radermacher, Aute, Tancabel…), 114 p. [OSTI 2293536](https://www.osti.gov/biblio/2293536).

**Méthode (p. 24-30, 50)** : tubes non ronds à forme NURBS, 15 variables (tableau 10 : h_t, w_t/h_t,
N_t, N_r, P_t/h_t, P_l/w_t, 3 points de contrôle x/y, vitesse d'air, 2 variables de passes).
Optimisation assistée par métamodèle : 5 000 designs (hypercube latin), CFD 2D Fluent k-ε réalisable,
2 673 convergés, krigeage (h, Δp air), vérifié sur 544 cas ; MOGA bi-objectif min Δp air et volume,
à puissance égale, contrainte de contrainte mécanique (cuivre, FS 3). Convergence maillage : GCI
sur 3 maillages, rapport 1,3.

**Résultats d'optimisation** : forme libre = jusqu'à 8,2× moins de volume, 5,5× moins de matière,
6× moins de volume interne à Δp égale (p. 51), mais formes pas toutes fabricables ; forme fixe NTHX1
fabricable. Condenseur **R290 2,4 kW** : Δp air −43 %, volume −69 %, surface frontale −14 %, volume
interne −49 % (tableau 22 ; Tancabel, Aute, Ling, IIR Gustav Lorentzen 2020).

**Essai système (p. 82-94), évaporateur NTHX retrofité dans un climatiseur R410A 8,4 kW** :
COP **−9,7 %**, puissance −11 %, charge −15 % seulement. Causes : **ponts de condensat** (Δp air
humide ×2,5 sur le prototype n° 1, p. 79), **mauvaise distribution du réfrigérant**, **collecteurs
surdimensionnés** (volume interne, charge). Pression d'évaporation −135 kPa. Simulation validée à ±10 %.
Un évaporateur correctement dimensionné permettrait +10 à 15 % de COP ; jusqu'à −60 % de charge en
simulation (COP −4 à −7 %).

**Autres points** : prototype aluminium brasé rompu à l'essai d'éclatement ; fuites aux jonctions
tube / collecteur (cuivre) ; modèle de bruit aéroacoustique (vitesses frontales > 1 m/s des faisceaux
compacts) ; corrélations côté tube pour canaux non ronds développées par CFD ; corrélations du nombre de
Lewis (déshumidification) pour faisceaux non ronds. Fabrication additive : épaisseur d'ailette métal
sûre 0,3 mm, limite actuelle 0,15 mm, projection 0,05 mm (DMLS, Arie et al.) — parois sous pression : plus.

**Non traité, listé en perspectives (p. 95)** : **givrage**, encrassement, corrosion, vibrations,
validité des corrélations diphasiques dans les petits canaux non ronds.

**Références à lire ensuite** : Tancabel et al., *Appl. Therm. Eng.* 216 (2022) 118965,
doi 10.1016/j.applthermaleng.2022.118965 ; Tancabel, Aute, Ling, « Optimization of R290 heat exchangers
utilizing high performance, non-round tubes », IIR Gustav Lorentzen 2020.

**Fabrication des prototypes (tableau 23, p. 66)** : 9 prototypes sur 10 conventionnels (tubes non
ronds en cuivre, collecteurs laiton, brasure Sn-Ag ; tubes aluminium extrudés). **Un seul imprimé en
3D métal : ENTHX-001, titane, radiateur air / eau 3,2 kW, fuyait dès ~20 psig (1,4 bar)** (3 tubes) ;
Δp air prédite à ±40 % seulement, attribué à la rugosité d'impression. 5 prototypes sur 11 ont fui ou
échoué à l'essai de pression. Génération précédente (Bacellar et al. [16]) prototypée en DMLS
(+60 % de densité d'échange massique). Revue AM : rugosité DMLS → +63 % (surfaces planes) / +35 %
(ailettes) d'échange (Ventola) mais plus de Δp ; ajouter de la surface (treillis) n'améliore pas
forcément l'échange (Wong). Piste d'étanchéité des pièces imprimées : épaisseur de paroi, HIP, essai
d'éclatement précoce.

### Articles du groupe UMD à lire (liens)

| Réf. | Accès |
|---|---|
| Tancabel et al., « Multi-scale and multi-physics analysis, design optimization, and experimental validation of heat exchangers utilizing high performance, non-round tubes », *Appl. Therm. Eng.* 216 (2022) 118965 | [doi](https://doi.org/10.1016/j.applthermaleng.2022.118965) ; manuscrit OSTI : [2418602](https://www.osti.gov/biblio/2418602) |
| Tancabel, Aute, Ling, « Optimization of R290 heat exchangers utilizing high performance, non-round tubes », 14e conf. IIR Gustav Lorentzen (GL2020), Kyoto, 6 p. | [IIR fridoc](https://iifiir.org/en/fridoc/optimization-of-r290-heat-exchangers-utilizing-high-performance-142980), [doi 10.18462/iir.gl.2020.1131](http://dx.doi.org/10.18462/iir.gl.2020.1131) (payant : 20 €, gratuit membres IIR) |
| O'Malley, Tancabel, Aute, « Optimization of R290 variable geometry heat exchangers », GL2024 | [OSTI 2448605](https://www.osti.gov/biblio/2448605), [IIR](https://iifiir.org/en/fridoc/optimization-of-r290-variable-geometry-heat-exchangers-149112) |
| Tancabel, thèse de doctorat UMD 2022 : « An integrated, multi-physics analysis and design optimization framework for air-to-refrigerant heat exchangers with shape optimized tubes » | à chercher sur DRUM (drum.lib.umd.edu) |
| Klein, thèse UMD 2023 : « Development of variable tube geometry heat exchangers using adjoint method with performance evaluation of an additively manufactured prototype » | à chercher sur DRUM |
| Article CLIMA 2022 (même groupe, condenseur de climatiseur résidentiel) | [PDF TU Delft](https://proceedings.open.tudelft.nl/clima2022/article/download/245/226/235) |
| A-type HX à tubes non ronds optimisés | [OSTI 1808321](https://www.osti.gov/biblio/1808321) |

## 8. Lecture détaillée : Tancabel, Aute, Ling, GL2020 (article R290, `docs/1131-30027955.pdf`)

- **Cas** : condenseur air / R290 d'un climatiseur (référence : tube-ailettes, tubes cuivre Ø 5 mm,
  Ren et al. 2014 ; 2,4 kW d'après le rapport DOE). **Condenseur seulement, régime sec, pas d'essai.**
- **Tube** : forme NURBS **fixée** (NTHX1, profil en lentille, fabriqué en cuivre et en aluminium,
  tient 20 MPa sans déformation notable). 14 variables continues (taille, pas, rangs, vitesse…), 2 passes.
- **CFD** : 2D, Fluent k-ε réalisable, paroi isotherme, périodique haut/bas ; h par UA-LMTD ;
  GCI 3 maillages (h : GCI ≤ 10 % pour 96 % des designs ; Δp : 91 %, pire cas 55 %).
- **Métamodèle** : krigeage sur 5 000 designs (hypercube latin), vérifié sur 544 :
  h à ±10 % pour 98 % des cas, **Δp à ±10 % pour 71 % seulement** (91 % à ±20 %).
- **Optimisation** : min Δp air et volume ; Q_BL ≤ Q ≤ 1,1 Q_BL, Δp_ref ≤ réf., V ≤ 0,8 V_BL,
  surface frontale ≤ réf., 0,5 ≤ H/L ≤ 2. Réfrigérant : Gnielinski / Shah 2016 (h), Churchill /
  Xu-Fang 2013 (Δp) ; charge avec la fraction de vide Ali-Sadatomi-Kawaji (la plus prudente).
- **Résultats** : à Δp air de référence : volume −69 %, matière −30 %, volume interne −50 %,
  **charge −48 %** ; ou volume −44 % avec Δp −43 %, matière −13 %, volume interne −37 %, charge −38 % ;
  surface frontale jusqu'à −15 %.
- **Non évalué** : COP de la machine, évaporateur, humide, givre, collecteurs, prototype (perspective).

## 9. Lecture détaillée : O'Malley, Tancabel, Aute, GL2024 (géométrie variable, PDF dans `docs/`)

« Optimization of air-to-R290 variable geometry heat exchangers », 16e conf. IIR Gustav Lorentzen,
College Park, 2024, doi 10.18462/iir.gl2024.1263 (projet DOE DE-EE0009677).

- **Idée** : échangeur à **géométrie variable** : 2 passes de réfrigérant en **contre-courant croisé**
  (air traverse HX1 puis HX2, réfrigérant entre dans HX2 côté sortie d'air), chaque passe ayant
  ses propres pas, nombre de tubes, rangs et vitesse d'air. Même tube NURBS fixe (Bacellar 2017),
  mêmes métamodèles CFD (Tancabel 2022) : **aucune nouvelle CFD**.
- **Optimisation séquentielle** : HX2 d'abord (0,50–0,55 Q_BL), puis HX1 avec les conditions de sortie
  de HX2 ; sous-refroidissement à 1 K près de la référence ; dimensions HX1 = HX2 à ±2 %.
- **Résultats (condenseur R290, réf. tube-ailettes Ø 5 mm)** : volume −60 % et plus, Δp air jusqu'à −24 %,
  surface frontale ~−30 %, matière −45 %, **charge −64 % et plus**. Face à Tancabel 2020 à Δp et volume
  égaux : surface frontale −25 %, **charge −36 %**, matière −28 %.
- **Pourquoi** : plus de surface dans la 2e passe (sous-refroidissement) + contre-courant → la zone
  liquide (la plus chargée) devient beaucoup plus petite. h air > 2× la réf., surface primaire > 4×,
  pas d'ailettes donc pas de pertes de rendement d'ailette.
- **Limites reconnues** : cœur seul (collecteurs non comptés), pas de mauvaise distribution,
  risque de **séparation liquide / vapeur dans le collecteur intermédiaire** ; optimisation
  séquentielle qui bride l'exploration (une optimisation simultanée des deux passes permettrait
  moins de Δp en agrandissant la face) ; condenseur seul, sec, pas de prototype.
- Références citées utiles : Huang et al. 2015 (VGHX microcanaux R290, −28 % de matière ou volume) ;
  Ge et al. 2021 (plusieurs formes de tubes dans un même faisceau : Δp −27 %, +5,3 % de flux) ;
  > 50 % de la charge d'un système est souvent dans le condenseur (Li 2015, Andersson 2018, Chen 2019).

**Thèse de Klein (2023)** : E. W. Klein, « Development of variable tube geometry heat exchangers using
adjoint method with performance evaluation of an additively manufactured prototype », thèse UMD,
dir. R. Radermacher. [hdl 1903/29991](http://hdl.handle.net/1903/29991) ;
[PDF](https://drum.lib.umd.edu/bitstreams/77b1f03d-5310-4635-86ad-f6e35a55b819/download).
C'est le PDF cité plus haut comme « Thèse UMD, tubes nus optimisés » (Δp −40 à −50 %).
Optimisation adjointe (gradients, CFD commerciale) de tubes nus non ronds ; prototype radiateur
500 W imprimé en **polymère** : Δp prédite à ±15 %, échange à ±10 %.

## 10. Lecture détaillée : thèse de Klein (UMD 2023, PDF dans `docs/`, 260 p.)

- **Essais composants (ch. 2)** : 4 échangeurs à tubes nus non ronds 2-3 mm (R410A, R134a), sec /
  humide / condenseur / radiateur. Δp air prédite à ±37 %, puissance à ±15 %. **Humide : Δp +111 à +160 %**
  à vitesse égale (1-2,5 m/s), autant ou plus que des tube-ailettes à pas 1-2 mm (+11 à +120 %) ;
  SHR 0,70-0,74 (≈ 10 % plus bas qu'un tube-ailettes : déshumidifie bien).
- **Essai système (ch. 3)** : climatiseur 7-8,8 kW, évaporateur tube-ailettes remplacé par CNTHX-FS :
  **puissance −30,4 %, COP −29,4 %, charge −12 %** (1re installation ; le rapport DOE donne −9,7 % de COP
  après corrections : joint, orifices de sortie agrandis). Causes : mauvaise distribution + ponts de
  condensat, attribués à **l'orientation (tubes horizontaux)**, aux orifices d'entrée / sortie
  sous-dimensionnés et mal orientés, et au montage des collecteurs.
- **Optimisation adjointe (ch. 4)** : Fluent, adjoint discret, ε-contrainte + pénalité, 2D quinconce,
  2-4 rangs, Dh 0,5-10 mm, ~100 designs : max ΔT air sous contrainte Δp. **Δp −40 à −50 % avec jusqu'à
  +20 % de puissance** face aux tubes ronds ; mécanisme : profil profilé, point d'arrêt réduit,
  décollement repoussé au bord de fuite, sillage et lâchers tourbillonnaires réduits ; surface ↑, h ≈ ou ↓.
  Départ NTHX1 : Δp −40 à −50 % à puissance égale, h ↑, section réfrigérant −1 à −32 %.
  **NTHX1 à 3 m/s : j = 0,024, f = 0,060, j/f = 0,40 ; optimisés : j/f 0,49-0,57** (tableau 73 ; compacité
  ~1 200 m²/m³). Limites : optimum local, dépend du point de départ, du maillage, de l'objectif.
- **Prototype AOHX (4.6)** : radiateur 7 rangs 500 W, optimisé : Δp −47 %, capacité +6 %, h −13 %,
  surface +24 %, j/f 0,11 → 0,19. Imprimé en **polymère** (PolyJet, parois 1 mm, collecteurs ABS FDM
  collés à l'époxy). Mesures : Δp à ±15 %, capacité à ±10 %.
- **Perspectives** : imprimer en **métal** un design 1-3 mm (NTHX1 optimisé) et tester en évaporateur /
  condenseur ; contraindre la section côté réfrigérant ; quantifier l'effet de la rugosité ; humide.

## 11. Recherche de couverture (2026-11-08) : documents importants pas encore lus

**PAC de fenêtre, données terrain (notre produit)**
- ACEEE, « Cold Climate Room Heat Pump Field Study » (2026) : 13 Midea + 13 Gradient sur 3 zones climatiques —
  [PDF](https://www.aceee.org/wp-content/uploads/2026/08/cold-climate-room-heat-pump-field-study.pdf)
- NYSERDA Report 25-21 (Taitem), mesure et vérification du pilote NYCHA « Clean Heat for All » (72 unités, Woodside Houses) ;
  présentations : [BE-Ex 2025-01](https://be-exchange.org/wp-content/uploads/2025/01/20250116_CleanHeat_Slides-UPDATED.pdf),
  [BE-Ex 2025-10](https://be-exchange.org/wp-content/uploads/2025/10/10.15.25-Room-Heat-Pump-Expo-Presentation-for-web.pdf).
  Cahier des charges CH4A : 9 000 BTU/h à COP 1,85 à 17 °F (−8,3 °C).

**Groupe UMD (suite de nos lectures)**
- Tancabel, thèse UMD 2022 (méthode complète : CFD côté tube, FEA, bruit, Lewis) —
  [PDF DRUM](https://api.drum.lib.umd.edu/server/api/core/bitstreams/da92cd43-f83e-480d-948e-58fff1f41d18/content)
- Tancabel et al., Appl. Therm. Eng. 2022, manuscrit accepté — [OSTI](https://www.osti.gov/pages/servlets/purl/2418602)
- Bacellar, Aute, Huang, Radermacher, « Design optimization and validation of high-performance heat exchangers using
  approximation assisted optimization and additive manufacturing », Sci. Technol. Built Environ. 23(6) 896-911 (2017) :
  article fondateur, prototype imprimé (DMLS) ; thèse de Bacellar UMD 2016 (DRUM).
- Bacellar, Aute, Radermacher, « CFD-based correlation development for air side performance of finned and finless tube
  heat exchangers with small diameter tubes », Purdue IRACC 2014, paper 1410 (corrélations utilisables directement).
- Article Purdue sur CNTHX-1 en évaporateur humide / sec (mentionne le givre) —
  [PDF](https://docs.lib.purdue.edu/cgi/viewcontent.cgi?article=3263&context=iracc)

**Givre et dégivrage (manque n° 1)**
- ORNL, « A critical literature review of defrost technologies for heat pumps » — [PDF](https://info.ornl.gov/sites/publications/Files/Pub117976.pdf)
- Comparaison givre / dégivrage microcanaux vs tube-ailettes (givrage > 50 % plus rapide en microcanaux, eau résiduelle) —
  [IIR](https://iifiir.org/en/fridoc/comparison-of-frost-and-defrost-performance-between-microchannel-coil-26232)
- Modèle de dégivrage microcanaux avec drainage et rétention d'eau (superhydrophobe : −31,7 % d'énergie de dégivrage), 2023 —
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0360544223033625)
- Tubes plats : givre et rétention d'eau, 2022 — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1359431122012492)

**R290 au niveau système**
- Revue « Residential heat pump and air conditioning systems with propane (R290) », Appl. Therm. Eng. 2025 —
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1359431125001516)

**TPMS et treillis imprimés côté air**
- TPMS à cellule graduée 6 → 10 mm : +30 % d'échange pour +0,3 kPa, Sci. Rep. 2025 — [Nature](https://www.nature.com/articles/s41598-025-04940-2)
- Treillis métalliques imprimés côté air : conductance +95 % mais Δp ×2, IJHMT 2020 —
  [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0017931019355140)
- Revue des échangeurs imprimés — [OSTI 2335469](https://www.osti.gov/servlets/purl/2335469)
- Optimisation de l'épaisseur de paroi des TPMS deux fluides (2025) — [arXiv 2510.10622](https://arxiv.org/pdf/2510.10622)

## 12. Lecture détaillée : Oh et al., « Multifunctional gradations of TPMS architected heat exchanger… », Sci. Rep. 15:19931 (2025)

(PDF dans `docs/` ; doi 10.1038/s41598-025-04940-2 ; SeoulTech.)
- **Échangeur liquide / liquide** (eau-glycol 25 °C / eau 10 °C, 4-10 L/min), gyroïde feuillet à deux fluides,
  écoulement croisé. **Pas d'air, pas de réfrigérant.** CFD SimericsMP+, k-ε standard.
- **Trois gradations par manipulation du champ de distance signée (SDF)** :
  1. **filtrage** : canaux d'entrée / sortie coniques (Ø 12 → 6 mm) intégrés dans la structure, réservés à un fluide
     → **résistance à l'écoulement −50 %** (= collecteurs intégrés au TPMS) ;
  2. **taille de cellule graduée** l(x) linéaire (6 → 10 mm optimal) → zones mortes −36 %, distribution plus uniforme ;
  3. **niveau graduée** C(x) pour garder une **paroi constante de 0,5 mm** malgré la variation de cellule
     (sinon la paroi varie avec l : 0,48 → 0,96 mm pour l = 5 → 10 mm à C = 0,3).
- Gyroïde uniforme, paroi 0,5 mm : l = 6 / 8 / 10 mm → porosité 74 / 82 / 85 %, 515 / 387 / 288 m²/m³,
  Dh 3,0 / 4,3 / 6,0 mm ; **FEA à 5 MPa (50 bar) : contrainte max 57 / 44 / 36 MPa < limite élastique 140-200 MPa**.
- **Fabrication** : fusion laser sur lit de poudre (GE Concept Laser M2), **AlSi7Mg**, détail minimal 200 µm,
  **polissage chimique** (H3PO4 85 % + CuSO4) pour réduire la rugosité, contrôle par micro-tomographie ;
  paroi mesurée 0,533 ± 0,05 mm ; **étanche** en fonctionnement (pas d'essai d'éclatement publié).
- **Résultats mesurés** (gradué vs uniforme) : **capacité +30 %, Δp +0,3 kPa, j/f^1/3 +28 %**.
- Pour nous : collecteurs intégrés (contre la mauvaise distribution vue à l'UMD), paroi constante 0,5 mm qui tient
  50 bar en calcul (propane ≈ 25-30 bar), polissage chimique contre la rugosité, gradation de cellule dans la profondeur
  facile à ajouter à `pac_fenetre/tpms.py` et à la CFD.

Les PDF lus sont rangés dans `docs/` (non versionnés : droits d'éditeur) ; l'article Tancabel et al. 2022
(*Appl. Therm. Eng.*, « Multi-Scale and Multi-Physics Analysis… ») y est aussi, pas encore lu.
