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

## 4. Autres formes à retenir (recherche complémentaire)

**Moustache de phoque : le tube ondulé (intérêt fort).** La moustache du phoque veau-marin a une
section elliptique dont la taille et l'orientation ondulent le long de son axe. Ces ondulations
cassent les grands tourbillons du sillage : sillage plus petit, lâcher de tourbillons plus faible,
efforts latéraux bien plus faibles. Une équipe d'Embry-Riddle (Prasad et Ricklick) l'a appliquée à
des picots d'échangeur : en essais, en moyenne 13 % de perte de charge en moins pour 4,5 %
d'échange en moins par rapport à un picot elliptique, ou environ 9 % de performance thermique en
plus à perte de charge égale (un seul groupe, pas de réplication trouvée). Pour nous : c'est
**exactement notre problème** (tubes en travers du flux qui lâchent des tourbillons, voir le
balayage de l'étape 1) et c'est imprimable. Candidat pour l'étape 3 : ellipse 2:1 ondulée le long
du tube, à calculer en CFD 3D (la 2D ne peut pas représenter l'ondulation).

**Ailes de chouette, queue de poisson : le ventilateur (intérêt fort pour le bruit).** Les plumes
de chouette ont un peigne au bord d'attaque et une frange au bord de fuite, qui rendent le vol
silencieux. Une étude (Xi'an Jiaotong) sur un ventilateur axial avec profil de chouette et bord de
fuite en dents de scie rapporte 2 dB de moins et 4,7 % de débit en plus ; une autre (Huazhong),
sur le ventilateur d'une unité extérieure de climatiseur, utilise un bord de fuite fourchu inspiré
de la queue de poisson. Attention : certains bords d'attaque modifiés dégradent le débit. Le bruit
est un critère majeur pour un appareil dans la pièce : piste pour le choix et le dessin du
ventilateur (dossier `ventilateurs/`).

**Phyllotaxie (tournesol) : l'agencement des tubes (intérêt moyen).** Disposer des picots selon
la spirale de Fibonacci du tournesol (angle d'or) : études sur des puits thermiques électroniques
(température maximale plus basse qu'en quinconce, - 14,7 % de température de surface dans une
autre étude) et un brevet d'échangeur radial. Surtout pertinent pour un **échangeur en disque à
écoulement radial**, à rapprocher de l'idée de la toile d'araignée. Peu de preuves face au
quinconce dans un écoulement droit comme le nôtre.

**Poumon d'oiseau : séparer ventilation et échange (intérêt moyen).** Chez l'oiseau, des sacs
aériens font circuler l'air et un tissu rigide (parabronches) fait l'échange ; l'air y passe dans
un seul sens, perpendiculairement au sang (« courant croisé »), et le sang peut ressortir plus
riche en oxygène que l'air sortant. C'est le principe de nos batteries (flux d'air unique, propane
en travers). Leçon pour l'arrangement des circuits : un courant croisé à plusieurs passes, disposé
à contre-courant global, se rapproche du contre-courant pur (déjà connu en ingénierie).

**Contre-courant des pattes d'oiseaux et des thons (rete mirabile).** Artères et veines côte à
côte en sens opposés : la chaleur passe de l'une à l'autre. Même leçon : circuits à contre-courant
air / propane pour gagner sur la surchauffe et le sous-refroidissement.

**Ailettes « vascularisées » (oreille d'éléphant, de fennec).** Grande surface mince parcourue
par un réseau de vaisseaux. Pour nous : faire passer de petits canaux de propane **dans** les
ailettes, ce qui raccourcit le chemin de conduction et permet des ailettes plus fines ou plus
grandes. L'impression 3D le permet (c'est aussi l'esprit des TPMS en feuillet à deux fluides).
Je n'ai pas trouvé d'étude sous ce nom : idée à évaluer (charge ajoutée contre rendement
d'ailette gagné).

**Plante carnivore Nepenthes (surfaces glissantes imbibées de liquide).** Surface poreuse imbibée
d'un lubrifiant, sur laquelle l'eau et le givre glissent. Aucune application à un échangeur
trouvée dans cette recherche ; un revêtement hydrophile anti-givre allonge nettement les cycles
entre deux dégivrages. À garder pour l'étape 5, avec la mouillabilité alternée.

## Ce que je propose de faire de ces pistes

1. **Étape 4 (prioritaire)** : collecteur en arbre de Murray adapté au diphasique, dans le
   modèle de charge, avec le distributeur à orifices calibrés (voir `docs/plan_formes_simples.md`,
   section 10). C'est la piste la plus directement liée à notre contrainte de charge.
2. **Étape 3** : ajouter le bord d'attaque ondulé (tubercules) aux variantes d'ailettes, à côté des
   ailettes plates, ondulées et persiennées.
3. **Étape 5** : essais de mouillabilité alternée sur échantillons imprimés (condensats et givre).
4. Garder en réserve l'échangeur en disque à distribution radiale (toile d'araignée, phyllotaxie),
   si le ventilateur choisi est axial.
5. **Étape 3** : tube elliptique ondulé « moustache de phoque », en CFD 3D, face à l'ellipse 2:1 lisse.
6. **Ventilateur** : profils inspirés de la chouette (bord de fuite en dents de scie) pour le bruit.
7. **Étape 4** : arrangement des circuits à contre-courant global (poumon d'oiseau, rete mirabile)
   et ailettes vascularisées, dans le modèle de la machine.

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
* Picots « moustache de phoque » (Embry-Riddle) : https://erau.edu/research-and-innovation/projects/investigation-of-bio-inspired-cylinders-for-enhanced-heat-transfer ;
  https://commons.erau.edu/edt/589 ; https://openpolar.no/Record/ftembryriddleaun:oai:commons.erau.edu:publication-2844
* Ventilateur à profil de chouette (Xi'an Jiaotong) : https://zkxb.xjtu.edu.cn/en/article/doi/10.7652/xjtuxb202011010/ ;
  bords de fuite ondulés : https://jafmonline.net/article_2432.html ; https://www.mdpi.com/2075-1702/11/2/155
* Phyllotaxie et picots : https://www.bohrium.com/paper-details/multi-objective-optimization-of-a-fibonacci-phyllotaxis-micro-pin-fin-heat-sink/1000432247771234319-16844 ;
  https://eld.bl.uk/catalog/100131652937_0x000001 ; brevet radial : https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10627170
* Poumon d'oiseau, courant croisé : https://pmc.ncbi.nlm.nih.gov/articles/PMC2662944 ;
  https://publications.ersnet.org/content/erj/29/1/11
* Revêtement hydrophile anti-givre : https://iifiir.org/en/fridoc/application-study-of-a-new-anti-frosting-coating-for-a-fin-and-tube-130925
