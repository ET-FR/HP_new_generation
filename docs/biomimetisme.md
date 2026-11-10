# Biomimétisme : formes naturelles pour les échangeurs de la PAC de fenêtre

Note du 10 novembre 2026. Recherche bibliographique rapide (articles de revue et études récentes),
pistes classées selon nos contraintes : charge de propane ≤ 152 g, puissance de ventilation, givre
et condensats, impression 3D métal. Rien n'est encore calculé ici : ce sont des pistes à trier.

## Ce qu'il faut retenir

La nature n'a pas un seul « bon échangeur » : elle résout séparément trois problèmes que nous
avons aussi.

| Problème chez nous | Solution naturelle | Intérêt pour nous |
|---|---|---|
| **Répartir le propane entre 20 à 40 circuits avec un minimum de volume** (collecteurs) | arbres de ramification des vaisseaux et des poumons, **loi de Murray** ; nervures des feuilles, toile d'araignée | **fort** : c'est notre problème de charge (voir `outils/analytique/charge_propane.py`) |
| **Échanger côté air avec peu de perte de charge** | branchies (lamelles fines et espacées), renouvellement de couche limite, tourbillons du bord d'attaque des nageoires de baleine | moyen à fort : rejoint l'étape 3 (ailettes) et les TPMS |
| **Évacuer l'eau de condensation et retarder le givre** | surfaces à mouillabilité alternée (scarabée du Namib, épines de cactus, feuille de lotus) | **fort** pour la batterie extérieure en hiver, et peu étudié pour les PAC |

## 1. Réseaux de distribution : loi de Murray, poumons, feuilles, toile d'araignée

**Principe.** Dans un réseau qui se ramifie, le volume contenu et la puissance de pompage sont
minimaux ensemble pour un rapport de diamètres précis à chaque bifurcation : en laminaire, le
diamètre du canal parent vaut 2^(1/3) ≈ 1,26 fois celui de chacun des deux canaux enfants
(loi de Murray). Un rapport plus grand baisse la perte de charge mais augmente le volume, et
inversement. Minimiser le volume à dissipation donnée ou la dissipation à volume donné mène à la
même solution. Smink et Visser (J. Fluid Mech., 2025) étendent l'optimisation au turbulent et
citent les échangeurs comme application.

**Pour nous.** Le volume des collecteurs est la charge qui manque à notre estimation. Un
collecteur imprimé en arbre de Murray, qui se divise en 2 puis 4, 8, 16, 32 circuits, donnerait
la perte de charge voulue avec le volume minimal. Le diphasique complique la règle (le rapport
optimal change avec le titre de vapeur) : c'est un calcul à faire, pas une loi à appliquer telle
quelle. Les bifurcations à angle droit ont des pertes plus fortes que les bifurcations douces.

**Ordre de grandeur vérifié** (32 circuits de 2 mm, face de 30 cm) : arbre ≈ 7,9 cm³ contre
15,1 cm³ pour un collecteur droit de Ø 8 mm, soit ≈ 3 g de propane gagnés par collecteur côté
liquide. C'est secondaire devant les tubes (40 à 150 g) : le vrai intérêt de l'arbre est la
**répartition égale** entre circuits (même chemin pour tous). Voir `docs/figures/loi_murray.png`.

**Toile d'araignée.** Les études trouvées (2025-2026) portent sur des puits thermiques à
microcanaux de liquide pour l'électronique, pas sur l'air : un réseau de canaux radiaux et
circulaires. Une étude couplée à une optimisation multi-objectif rapporte + 35 % de coefficient
d'échange et - 8 % de perte de charge par rapport au dessin de départ ; une autre l'améliore par
optimisation topologique. Pour nous, la toile d'araignée est donc d'abord un **schéma de
distribution** (radial + circulaire, avec des boucles qui donnent plusieurs chemins), pas une
forme côté air. Idée à garder : un échangeur en disque devant un ventilateur axial rond, alimenté
au centre et distribué en rayons, épouserait le jet du ventilateur.

**Feuilles.** Les nervures forment des boucles fermées : un canal bouché (givre, impureté) est
contourné. Intéressant pour la robustesse, à mettre en balance avec le volume ajouté.

## 2. Côté air : branchies, nageoires de baleine

**Branchies de poisson.** Lamelles primaires et secondaires très fines ; les paramètres clés
identifiés sont la longueur des lamelles, leur surface et l'espacement entre lamelles (arXiv
1805.07744). C'est exactement le problème de l'écart optimal entre ailettes (Bejan) : la nature
retrouve un optimum de même nature. Les applications publiées sont des échangeurs à plaques pour
l'eau (+ 15 à 17 % d'échange par rapport à des plaques à chevrons), pas des batteries à air.

**Nageoires de baleine à bosse (tubercules).** Un bord d'attaque ondulé crée des tourbillons
longitudinaux contrarotatifs qui renforcent les échanges près de la paroi en laminaire et en
transition. Je n'ai trouvé aucune étude qui l'applique aux ailettes d'échangeur ; le mécanisme est
celui des générateurs de tourbillons, connus pour augmenter l'échange des ailettes plates.
Piste d'étape 3 : **bord d'attaque d'ailette ondulé**, facile à imprimer, à comparer aux
générateurs de tourbillons classiques. Effet secondaire possible sur le bruit (les bords ondulés
réduisent le bruit des profils).

**Écailles et peau de requin.** Les micro-reliefs réduisent la traînée en écoulement turbulent ;
nos écoulements sont laminaires, l'intérêt est faible.

**Gyroïde.** La forme TPMS gyroïde, déjà dans notre plan, existe dans la nature (structure des
écailles d'ailes de certains papillons). Le biomimétisme rejoint ici une piste que nous avons.

## 3. Eau et givre : mouillabilité alternée

**Principe.** Le scarabée du Namib capte l'eau du brouillard sur des zones hydrophiles entourées
de zones hydrophobes qui la font rouler ; les épines de cactus la font migrer dans une direction.
Sur une ailette : la condensation en gouttes (hydrophobe) se mêle à des chemins d'écoulement
(hydrophile) qui drainent l'eau.

**Résultats trouvés.**
* Surface en « épines » hydrophile / hydrophobe (Energies, 2019) : drainage plus rapide, givre
  retardé, coefficient d'échange en givrage + 16 % par rapport au cuivre nu. Les auteurs notent
  que la mouillabilité alternée a rarement été appliquée au givrage.
* Surface alternée (Int. J. Heat Mass Transfer, 2022) : + 21 % d'eau évacuée par rapport à une
  surface super-hydrophile, + 76 % par rapport à une surface hydrophobe.
* Revêtement super-hydrophobe d'échangeur en conditions humides (ORNL) : perte de charge côté air
  presque divisée par 2, les gouttes sautent de la surface avant de geler.

**Pour nous.** La pénalité humide (Δp × 2 à 2,5 sur tubes nus fins) est notée dans
`docs/plan_echangeurs.md` comme la cause n° 1 de l'échec des essais réels. Une surface imprimée
dont on structure la mouillabilité (rugosité, texture, revêtement) est une piste sérieuse et
peu explorée pour les PAC. Elle relève des essais physiques (étape 5) plus que de la CFD.

## Ce que je propose de faire de ces pistes

1. **Étape 4 (prioritaire)** : collecteur en arbre de Murray adapté au diphasique, dans le
   modèle de charge, avec le distributeur à orifices calibrés (voir `docs/plan_formes_simples.md`,
   section 10). C'est la piste la plus directement liée à notre contrainte de charge.
2. **Étape 3** : ajouter le bord d'attaque ondulé (tubercules) aux variantes d'ailettes, à côté des
   ailettes plates, ondulées et persiennées.
3. **Étape 5** : essais de mouillabilité alternée sur échantillons imprimés (condensats et givre).
4. Garder en réserve l'échangeur en disque à distribution radiale (toile d'araignée), si le
   ventilateur choisi est axial.

## Sources

* Revue multi-échelle des échangeurs bio-inspirés (Biomimetics, 2025) :
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12839163/ (le rapport de relecture signale une
  analyse critique mince : à lire comme un inventaire)
* Zhu et al., structures inspirées de la nature pour l'échange et la traînée (Micromachines, 2021) :
  https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8227078/
* Huang, Hwang et Radermacher, revue des échangeurs inspirés de la nature (Int. J. Refrigeration) :
  https://iifiir.org/en/fridoc/review-of-nature-inspired-heat-exchanger-technology-140766
* Smink et Visser, optimisation des réseaux ramifiés (J. Fluid Mech., 2025) :
  https://resolve.cambridge.org/core/services/aop-cambridge-core/content/view/02A336A447A689A1D9F288B0363071D2/S0022112025003933a.pdf/optimising-branched-fluidic-networks-a-unifying-approach-including-laminar-and-turbulent-flows-rough-walls-and-non-newtonian-fluids.pdf
* Brevet, distribution fractale (rapport 2^(1/3), compromis volume / perte de charge) :
  https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11660577
* Puits thermique en toile d'araignée (Fluid Dyn. Mater. Process., 2026) :
  https://www.techscience.com/fdmp/v22n4/67242
* Toile d'araignée, optimisation multi-objectif : https://synapsesocial.com/papers/W7128072128
* Revue citant l'optimisation topologique de la toile d'araignée :
  https://mfr.edp-open.org/articles/mfreview/pdf/2026/01/mfreview250078.pdf
* Branchies, paramètres de conception : https://www.arxiv.org/pdf/1805.07744
* Échangeur à plaques inspiré des branchies (Energy, 2022) :
  https://ideas.repec.org/a/eee/energy/v253y2022ics0360544222011100.html
* Effet tubercule : https://en.wikipedia.org/wiki/Tubercle_effect ; bords d'attaque ondulés en
  laminaire et transition : https://eres.library.adelaide.edu.au/dspace/bitstream/2440/106416/2/02whole.pdf
* Surface en épines hydrophile / hydrophobe et givrage (Energies, 2019) :
  https://mdpi.com/1996-1073/12/23/4471
* Surface alternée et évacuation des condensats (Int. J. Heat Mass Transfer, v. 194) :
  https://scholarworks.unist.ac.kr/handle/201301/58844
* Échangeur super-hydrophobe en conditions humides (ORNL) :
  https://impact.ornl.gov/en/publications/energy-saving-of-air-cooling-heat-exchangers-operating-under-wet-/
