# Ventilateurs : technologies de pales, biomimétisme, motorisation BLDC

Note du 11 novembre 2026. Recherche bibliographique rapide. Les gains annoncés par les fabricants
sont **des chiffres commerciaux, sans norme d'essai publiée** : ils sont signalés comme tels.
Les chiffres de nos propres points de fonctionnement sont dans `resultats_predimensionnement.md`.

## Ce qu'il faut retenir

1. **Le premier gain n'est pas la pale, c'est l'architecture autour.** Un axial libre perd en
   sortie une énergie cinétique ½ρc² du même ordre que les 25 Pa de la batterie (24 à 75 % de la
   pression totale selon le diamètre, voir le script). Diffuseur, stator redresseur, virole serrée
   et grand diamètre lent rapportent plus que n'importe quel motif bio-inspiré.
   Ordre de grandeur publié : un diffuseur fait passer un axial de 42 % à plus de 50 % de rendement
   global (ebm-papst, 1 250 mm).
2. **Le biomimétisme sert surtout le bruit**, et seulement de quelques points le rendement :
   dentelures de chouette −3 à −5 dB, tubercules de baleine surtout utiles hors point nominal
   (décrochage retardé), profils ondulés de libellule −2,5 dB sur une roue sirocco. Les gains de
   rendement chiffrés indépendants sont de 3 à 8 %, souvent au prix d'une perte au point nominal.
   Le bruit compte pour nous (fenêtre de chambre), donc on garde ces pistes, en deuxième rang.
3. **Moteur EC / BLDC à commande vectorielle (FOC) sans capteur : oui, sans hésitation.**
   PSC 30–50 %, pôles ombragés 15–25 %, EC 60–90 %, et le rendement reste presque plat en
   charge partielle, ce qui compte puisque la PAC tourne surtout à bas régime.
4. **Le budget 76 W du cahier des charges sous-estime le besoin** (il ne compte que 25 Pa) et
   surestime ce que donne un produit standard : le ventilateur EC 200 mm déjà dans le dépôt donne
   η ≈ 0,26 au mieux. Cible réaliste du dossier, revue après l'analyse des pertes (section 5) :
   **η global 0,45–0,55**, soit ≈ 45–55 W au total, ce qui vaut ≈ +0,4 point de COP à COP 6.
5. **Jeu en bout de pale : anneau tournant fixé aux pales, oui ; roulement en périphérie, non ;
   moteur en périphérie (rim-driven), intéressant mais trop cher pour le premier prototype**
   (section 6).

Pour essayer les variantes : `animation_ventilateur.html` (ventilateur animé, réglages et bilan des
pertes recalculés en direct).

## 1. Quelle famille de ventilateur

| Famille | Où elle gagne | Rendement global typique | Pour nous |
|---|---|---|---|
| **Axial à virole + diffuseur / stator** | grand débit, faible pression (notre cas) | 0,45–0,60 avec diffuseur | **extérieur : choix de base** |
| Contrarotatif (2 rotors) | plus de pression dans le même diamètre, giration récupérée | 63–65 % mesurés en 100–375 mm (Wang et al. 2015) | piste si le diamètre est limité par la fenêtre |
| Hélico-centrifuge (diagonal) | pression moyenne, compact | ≈ 0,48–0,56 (DiaForce, fabricant) | intérieur si la batterie TPMS est plus résistante que prévu |
| Centrifuge à aubes arrière (roue libre) | pression élevée, débit moyen | > 0,70 en grande taille (ZAbluefin) | intérieur possible, encombrant |
| Tangentiel (cross-flow) | sortie en nappe large, très plat, silencieux | faible, ≈ 0,2–0,4 (à vérifier dans Vanaei 2023) | standard des splits ; à éviter si on veut gagner des watts |

Règles physiques utiles :
- Lois de similitude : Q ∝ n D³, Δp ∝ n² D², P ∝ n³ D⁵. Diviser la vitesse par 2 divise la
  puissance par 8 : il vaut mieux un grand rotor lent, et le pilotage en vitesse variable est
  l'arme principale en charge partielle.
- Bruit ∝ u⁵ à u⁶ (vitesse de bout de pale) : même conclusion.
- Jeu en bout de pale : passer de 0,3 % à 0,1 % du diamètre gagne ≈ 2 points de rendement ; sous
  5 % de la hauteur de pale, le rendement baisse linéairement avec le jeu. Une virole tournante
  (« ring fan », pales reliées par un anneau) supprime le tourbillon de bout de pale.

## 2. Technologies de pales récentes (fabricants)

- **ebm-papst AxiBlade / AxiBlade.Perform (2025)** : profil aile, winglets intégrés, aubes
  directrices, diffuseur. Annonce : jusqu'à +54 % de rendement et −8 dB par rapport au « standard
  du marché », rendement statique jusqu'à 53 %.
- **ebm-papst AxiTop** (diffuseur seul) : mode rendement −27 % de puissance et −7,2 dB(A), ou
  +9 % de débit à puissance égale.
- **Ziehl-Abegg FE2owlet** (axial) : pales en faucille, bord de fuite dentelé (chouette),
  winglets ; −4 dB(A). Mahle en a tiré un ventilateur de refroidissement auto : +10 % de
  rendement, −10 % de masse.
- **Ziehl-Abegg ZAbluefin** (centrifuge) : bord d'attaque ondulé type nageoire de baleine,
  +10 à +15 % selon les sources.
- **LG MULTI V 5** : pales inspirées de la baleine, −20 % de consommation annoncés.
- **Sharp** : roue sirocco « aile de libellule » (section en dents de scie, petits tourbillons qui
  réduisent le frottement), −2,5 dB mesurés ; hélice extérieure inspirée de l'aigle, de
  l'albatros et du martinet (qualitatif).

## 3. Biomimétisme : ce que dit la recherche

| Modèle naturel | Motif | Effet mesuré | Prix à payer |
|---|---|---|---|
| **Chouette** | dentelures de bord d'attaque, peigne de bord de fuite, frange | −3 à −5 dB à moyenne et haute fréquence ; hélice avec les deux : −3,1 dB et +7,9 % de rendement de poussée (Phys. Fluids 2025) | au-dessous de 15° d'incidence, le bord dentelé dégrade l'aérodynamique (Chiba 2017) ; plus les dents sont longues, plus le bruit baisse et l'aéro se dégrade |
| **Baleine à bosse** | tubercules sinusoïdaux au bord d'attaque | décrochage retardé, tourbillons de bout réduits, couple réduit (hélices marines, CFD) ; ventilateurs : chiffres seulement commerciaux | léger déficit au point nominal ; gain surtout hors nominal, utile avec un givre qui monte la perte de charge |
| **Libellule** | section ondulée (corrugation) | −2,5 dB (Sharp, sirocco) ; rigidité d'une pale très mince | profil plus délicat à mouler |
| **Harle / oiseaux** | profil d'aile d'oiseau sur roue tangentielle | −3,3 % de puissance à débit égal (Xi'an Jiaotong) | gain modeste |
| **Bout d'aile d'oiseau** | winglets, rémiges écartées | réduit le tourbillon de bout de pale | — |

Lecture pour nous : le point de fonctionnement d'une batterie extérieure **qui givre** glisse vers
les faibles débits et les fortes incidences, là où les tubercules et les dentelures sont justement
favorables (décrochage retardé, moins de bruit de décrochage tournant). C'est l'argument le plus
solide pour un motif bio-inspiré chez nous.

## 4. Motorisation : petit BLDC + FOC sans capteur

- **Pourquoi** : rendement moteur 80–90 % en petite puissance contre 30–50 % pour un PSC, courbe
  plate en charge partielle, vitesse continue (on suit la puissance de la PAC au lieu de 3
  vitesses), démarrage doux, mesure de vitesse et de couple gratuite (détection d'encrassement ou
  de givre par la hausse du couple à vitesse donnée).
- **Moteur** : rotor extérieur intégré au moyeu (le moteur EC classique des ventilateurs) ; il
  libère de la place, la cloche sert de moyeu.
- **Électronique « sans code »** :
  - TI **MCF8316A / C / D** : FOC sans capteur intégré, 4,5–35 V, 8 A crête, identification
    automatique des paramètres du moteur, consigne PWM / analogique / I²C. Bon pour prototyper.
  - Fortior **FT8132** (pré-driver, MOSFET externes, 28 V) et famille FT8213 / FT8215 / FS9276
    (ce dernier listé pour unités intérieures de clim) : réglage par interface graphique,
    paramètres en EEPROM. C'est la filière bon marché des ventilateurs chinois en volume.
  - Alternatives à regarder : Infineon iMOTION (IMD110), ST STSPIN32.
- **Alimentation** : un bus DC commun (24 V, ou le bus haute tension de l'onduleur du
  compresseur pour éviter un étage de conversion) ; à trancher avec l'électronique de la PAC.

## 5. Pourquoi le rendement d'un petit ventilateur est si bas

Quatre causes se cumulent ; les deux premières sont physiques et nous suivent quel que soit le
dessin.

1. **Pression utile faible : l'air sortant emporte une grosse part de l'énergie.** Le rendement
   statique ne compte que la pression gagnée sur la batterie. W1G200 à 320 m³/h : section annulaire
   ≈ 250 cm², air sortant à 3,5 m/s, ½ρc² ≈ 7,5 Pa perdus, soit 25 % de la pression totale.
   À 1 000 Pa (centrifuge), ce serait négligeable ; à 25 Pa, c'est structurel.
2. **Faible nombre de Reynolds.** Re = vitesse × corde / viscosité ≈ 55 000 pour le W1G200, ≈ 100 000
   pour un rotor de 500 mm à 600 tr/min, contre ≈ 10⁷ pour une aile d'avion. Sous ≈ 10⁵, la finesse
   d'un profil tombe de ≈ 100 à 20–40 (couche limite laminaire, bulle de décollement). C'est le
   régime des oiseaux et des insectes : profils minces cambrés, dentelures et ondulations y sont
   adaptés.
3. **Bout de pale et giration.** 1 à 2 mm de jeu sur 200 mm, c'est 3 à 10 fois plus en proportion
   que sur un grand ventilateur ; et sans stator la rotation de l'air en sortie est perdue.
4. **Petit moteur et électronique.** À 8 W, roulements, pertes fer, alimentation de la commande et
   redresseur 230 V pèsent lourd : ≈ 60–70 % pour le moteur, contre plus de 90 % à 1 kW.

Bilan estimé du W1G200 à son meilleur point (320 m³/h, 23 Pa). Seules l'entrée et la sortie
viennent de la fiche ; la répartition est estimée.

| Poste | W | Part |
|---|---|---|
| Électricité absorbée | 8,0 | 100 % |
| Électronique (redresseur, commande) | ≈ 1,0 | 12 % |
| Moteur (cuivre, fer, roulements) | ≈ 2,3 | 29 % |
| Aérodynamique (profil à faible Re, jeu, giration) | ≈ 1,9 | 24 % |
| Air sortant (½ρc²) | 0,7 | 9 % |
| **Pression utile sur la batterie** | **2,0** | **26 %** |

Ce que nous pouvons attaquer : le moteur et l'électronique (BLDC + FOC à 15–40 W : 80–85 %), l'air
sortant et la giration (diffuseur, stator), le bout de pale (anneau, section 6). Le faible Reynolds
ne se supprime pas, il se repousse (grand diamètre, corde large, profil choisi pour ce régime).
D'où la cible revue de 0,45–0,55.

## 6. Jeu en bout de pale : anneau tournant, roulement périphérique, rim-driven

| Solution | Principe | Pour | Contre | Décision |
|---|---|---|---|---|
| Pales libres, jeu serré | standard | simple | perte ≈ 2,85 × jeu / hauteur de pale ; bruit de jeu ; tolérances serrées | référence |
| **Anneau tournant fixé aux pales** (« ring fan », ventilateurs auto) | plus de tourbillon de bout de pale | fuite reportée entre anneau et carter, moins nuisible et réduite par un joint sans contact (lèvre dans une gorge du pavillon, labyrinthe) ; pales rigidifiées, donc plus minces ; jeu de 2–3 mm toléré (fabrication, givre) | frottement de l'air sur l'anneau ≈ 1 W à 500 mm ; un peu d'inertie | **retenu, à comparer en CFD (jeu 1 à 3 mm)** |
| Anneau porté par un roulement en périphérie | appui à la périphérie au lieu du moyeu | — | couple de frottement ∝ diamètre : graisse et joints d'un roulement fin de 500 mm, quelques à plusieurs dizaines de W à 600 tr/min (à vérifier sur catalogue) ; givre, eau, poussière dans le contact ; bruit transmis au carter ; coût élevé | **écarté** |
| Moteur en périphérie (rim-driven, moyeu supprimé) | aimants dans l'anneau, bobinage dans le carter | sans moyeu : +14 % de section (moyeu 0,35 D), −23 % d'énergie de sortie | entrefer ≈ 1 mm sur 500 mm, aimants coûteux, paliers à l'air froid et humide | **intéressant mais trop cher : hors premier prototype** |

Gain attendu de l'anneau : quelques points de rendement (2 à 5 estimés, pas encore de mesure sur un
ventilateur comparable).

## 7. Quelle pale pour notre système

Notre cas : axial à 25 Pa, Ø 500 mm à ≈ 500–600 tr/min (extérieur), Ø 280 mm à ≈ 1 000 tr/min
(intérieur), Reynolds de pale 50 000–150 000. Détail et sources : section « Quelle pale pour notre
système » de `ventilateurs.html`.

| Choix | Ce que dit la recherche | Pour nous |
|---|---|---|
| Profil | sous Re ≈ 10⁵, plaque cambrée mince (arc de cercle, 3 % d'épaisseur, bords arrondis) ≥ profils épais type NACA, dont la traînée explose à bas Re (Balla et Vad, AIAA J. 2022 : modèles mesurés Re 40–140 k, cambrure 0–8 % ; NASA Ames 2020) | plaque cambrée 4–7 %, 3 % d'épaisseur |
| Nombre de pales | hélices de PAC : 3 pales très larges, semi-carénées ; exemple 401 mm, 3 pales, moyeu 0,25, corde 67 → 318 mm, 839 tr/min, 1 780 m³/h, rendement total 65 → 68 % (Frontiers 2021) | 3 à 4 pales larges : Re doublé à solidité égale |
| Répartition radiale | tourbillon contrôlé : +4,2 points (JAFM 2025), +3,9 à 4,6 points à faible moyeu (thèse Twente 2021) | tourbillon contrôlé, moyeu 0,25–0,30 |
| Faucille | avant : +3 points, −1,1 dB (PAC 401 mm) ; moins de bruit sur 495 mm ; arrière meilleure hors nominal | faucille avant modérée, à vérifier givré |
| Bout de pale | anneau tournant + labyrinthe (brevets automobiles, Gênes 2019) | retenu |
| Installation | pavillon redessiné +1,2 % ; optimiser la pale montée dans l'unité, l'air de la batterie n'est pas uniforme | CFD avec batterie et pavillon |

Modèle de l'animation (500 mm optimisé, calage 34°) : 3 pales de 250 mm η = 0,608 contre 7 pales de
110 mm η = 0,594, à ≈ 500 tr/min dans les deux cas ; profil bas Re +3 à 4 points sur la plaque standard.
Tendances seulement : elles découlent de la loi de traînée supposée.

**Pale de départ.** Extérieur : Ø 500 mm, moyeu 0,25–0,30, 3 à 4 pales, corde ≈ 150 mm au pied →
220–250 mm au bout, plaque cambrée 5–6 % / 3 %, tourbillon contrôlé, faucille avant modérée, anneau +
labyrinthe, bord de fuite dentelé, ≈ 500–550 tr/min. Intérieur : Ø 280 mm, même famille, 5 pales,
corde ≈ 90–110 mm.

## 8. Les autres formes de roue (blower, centrifuge, tangentielle)

**Climatiseur de fenêtre classique** (manuel Friedrich, moteurs Fasco) : un moteur PSC à double arbre
entraîne la **roue blower** (centrifuge à aubes avant) côté pièce et l'**hélice « slinger »** côté
extérieur. La slinger est une axiale à anneau en bout de pales (déjà un « ring fan ») qui projette le
condensat sur le condenseur. Notre PAC : 2 BLDC indépendants (dégivrage : extérieur seul), pas de
slinger en chauffage (givre).

| Famille | ψ | Rendement de pointe publié | Pour nous |
|---|---|---|---|
| Roue blower (sirocco, aubes avant) | ≈ 2–3 | statique 0,55–0,68 (grandes roues) | intérieur si la place manque : Ø 160 × 170 mm à ≈ 600 tr/min pour 800 m³/h, tourne l'air de 90°, très silencieuse |
| Centrifuge aubes arrière | ≈ 0,8–1,1 | ≤ 0,80 (profilée ≤ 0,84) ; module EC 250 mm : global 0,47–0,56 | seulement si la perte de charge intérieure dépasse nettement 25 Pa |
| Tangentielle (cross-flow) | ≈ 2 | faible | nappe large et plate (splits muraux) ; à éviter pour les watts |
| Diagonale | ≈ 0,4–0,6 | ≈ 0,48–0,56 | intermédiaire |
| Axiale | ≈ 0,1–0,3 | 0,45–0,60 avec diffuseur | **extérieur** ; intérieur Ø 280 mm si profondeur et caisson de virage |

Tailles intérieures calculées pour 40 Pa (25 Pa de batterie + ≈ 15 Pa de grille et de virage),
coefficients de débit supposés : ordres de grandeur. Le choix intérieur dépend de la géométrie de la
fenêtre, comme le diamètre maximal. Détail, schémas et sources : `ventilateurs.html`, section
« Les autres formes de roue ».

## 9. Même ventilateur et même échangeur des deux côtés (choix du 11/11/2026)

Un seul module (batterie + ventilateur de 500 mm) monté côté pièce et côté façade
(`outils/module_commun.py`). Dimensionné sur le besoin extérieur le plus fort à 2 500 m³/h : avec
les Te / Tc actuels de la fiche échangeur, c'est **la clim à 35 °C (1 104 W/K)**, plus que le
chauffage à −8,3 °C (897 W/K).

| Point | Intérieur | Extérieur | Ventilateurs | Budget fiche |
|---|---|---|---|---|
| Clim 35 °C | 570 m³/h, 125 tr/min, 1,4 W | 2 500 m³/h, 498 tr/min, 28,6 W | 30 W | 72 W |
| Chauffage 8,3 °C | 830 m³/h, 177 tr/min, 2,2 W | 1 690 m³/h, 345 tr/min, 10,2 W | 12 W | 76 W |
| Chauffage −8,3 °C | 830 m³/h, 177 tr/min, 2,2 W | 2 160 m³/h, 434 tr/min, 19,3 W | 22 W | 76 W |
| Chauffage −15 °C | 830 m³/h, 177 tr/min, 2,2 W | 1 700 m³/h, 346 tr/min, 10,3 W | 13 W | 76 W |

- Même batterie, même circuit d'air : le ventilateur reste à son point de dessin à toutes les
  vitesses (seul le Reynolds baisse côté pièce). Côté pièce, 3 à 5 m/s en bout de pale : quasi
  inaudible.
- La batterie intérieure plus grande permet de baisser Tc : à 8,3 °C, en passant de 830 à
  1 200 m³/h, Tc 32 → 29 °C, compresseur 355 → 318 W, ventilateur +2,3 W : **≈ −35 W (≈ 10 %)**.
  Au-delà, air soufflé sous 27 °C.
- À vérifier : encombrement côté pièce (≈ 0,4–0,5 m² de batterie, rotor de 500 mm), volume de
  propane (≤ 279 cm³ par batterie, déjà au cahier des charges), condensat et dégivrage, moteur de
  125 à 500 tr/min et de 1,4 à 30 W, portée du jet d'air.

## 10. Pistes de travail proposées

1. Fixer l'encombrement disponible dans la fenêtre (diamètre max de chaque ventilateur) : c'est
   lui qui décide de la perte de sortie et donc de tout le reste.
2. Refaire le budget de ventilation avec la pression totale (25 Pa + perte de sortie − récupération
   du diffuseur), pas seulement 25 Pa : à corriger aussi dans `conception_echangeur/outils/analytique/pac_calc.py`.
3. Concevoir une pale de base axiale (méthode de l'élément de pale, ψ ≈ 0,2, vortex libre ou
   contrôlé), puis la comparer en CFD 3D (OpenFOAM, MRF) avec : stator redresseur, diffuseur,
   bord d'attaque à tubercules, bord de fuite dentelé, winglets, anneau tournant (jeu 1 à 3 mm,
   avec et sans labyrinthe). Choisir un profil adapté à Re ≈ 50 000–100 000.
4. Point extérieur givré : vérifier que la pale ne décroche pas quand la perte de charge double.
5. Prototype : impression 3D de la pale + moteur BLDC rotor extérieur + carte d'évaluation MCF8316,
   mesure débit / pression / puissance sur un petit banc (boîte à débit normalisée ISO 5801).

## Sources

- Agrawal et Sharma, bords d'attaque dentelés (AIAA 2016), Iowa State :
  <https://dr.lib.iastate.edu/entities/publication/7628929b-0c75-4202-8ecc-9e165a324645>
- Chiba University, dentelures et incidence (Bioinspir. Biomim. 2017) :
  <https://www.sciencedaily.com/releases/2017/07/170704093621.htm>
- Hélice biomimétique, dentelures de chouette bord d'attaque + fuite (Phys. Fluids 2025) :
  <https://www.ebsco.com/articles/chemistry/a2779745-54b9-5e5a-a4fc-1d678df0ef2d/experimental-investigation-of-a-biomimetic-propeller-coupled-with-owl-inspired-leading-and-trailing-edges-serrations>
- Mémoire PolyU, densité des dentelures : <https://theses.lib.polyu.edu.hk/handle/200/10116>
- Falchi et al., tubercules sur hélices marines (Ocean Eng. 2022) :
  <https://strathprints.strath.ac.uk/80727/1/Falchi_etal_OE_2022_effect_of_leading_edge_tubercles_on_the_performance_of_marine_propellers.pdf>
- WhalePower, tubercules (MIT Technology Review 2008) :
  <https://www.technologyreview.com/2008/03/06/221447/whale-inspired-wind-turbines/>
- Revue de conception des rotors axiaux à bord d'attaque sinusoïdal (Energies 2024) :
  <https://doaj.org/article/49e25c189677480097639621c0b9dfc4>
- Revue bio-inspiration et bruit aérodynamique (Appl. Sci. 2019) : <https://mdpi.com/2076-3417/9/11/2224>
- Revue pales bio-inspirées éolien / marin (2025) :
  <https://tethys-engineering.pnnl.gov/sites/default/files/publications/RevathiRamakrishnan-2025.pdf>
- ebm-papst AxiBlade.Perform (2025) :
  <https://www.ebmpapst.com/ae/en/newsroom/news/2025/new-axiblade-perform-ec-technology.html>
- ebm-papst, genèse de l'AxiBlade : <https://mag.ebmpapst.com/en/?p=11258>
- ebm-papst AxiTop : <https://www.climatecontrolnews.com.au/news/axitop-sets-new-standard-in-acoustics>
- ebm-papst, axial ou centrifuge pour PAC :
  <https://www.ebmpapst.com.cn/en/newsroom/news/2020/fans-for-air-water-heat-pumps.html>
- Ziehl-Abegg, bionique : <https://www.ziehl-abegg.com/en/glossary/bionics-biomimetics>
- Ziehl-Abegg ZAbluefin : <https://www.climatecontrolnews.com.au/interviews/bionic-profiling-delivers-peak-efficiency>
- Mahle, ventilateur chouette : <https://newatlas.com/automotive/mahle-biomimetic-owl-cooling-fan>
- Sharp, roue libellule (rapport technique) : <https://corporate.jp.sharp/rd/n39/pdf/107_09.pdf>
- Sharp, biomimétisme unité extérieure : <https://www.vn.sharp/en/microsite/biomimetic/air-conditioner-outdoor>
- Roue tangentielle à pales d'aile de harle (Xi'an Jiaotong) :
  <https://scholar.xjtu.edu.cn/zh/publications/%E9%87%87%E7%94%A8%E4%BB%BF%E7%A7%8B%E6%B2%99%E9%B8%AD%E7%BF%BC%E5%9E%8B%E5%8F%B6%E7%89%87%E8%B4%AF%E6%B5%81%E9%A3%8E%E6%9C%BA%E7%9A%84%E6%B0%94%E5%8A%A8%E6%80%A7%E8%83%BD%E6%95%B0%E5%80%BC%E7%A0%94%E7%A9%B6/>
- LG, biomimétisme HVAC : <https://www.lghvacstory.com/?p=3076>
- Vanaei et al., revue des ventilateurs tangentiels (Energies 2023) :
  <https://sam.ensam.eu/bitstream/10985/26216/2/LIFSE_E_2023_VANAEI.pdf>
- Himeur et al., performance des ventilateurs tangentiels (Energies 2022) :
  <https://mdpi.com/1996-1073/15/14/5134/htm>
- Wang, Ravelet, Bakir, ventilateurs contrarotatifs (2015) :
  <https://sam.ensam.eu/bitstream/10985/9486/3/Dynfluid-JEPS-WANG-2015-1.pdf>
- Contrarotatif, espacement et répartition de charge : <https://pdf.arxiv.org/pdf/1208.6396>
- Jeu en bout de pale, winglets, hauteur de virole :
  <https://iifiir.org/en/fridoc/effect-of-tip-clearance-winglets-and-shroud-height-on-the-tip-141441>
- Jeu en bout de pale, ventilateur 806 mm : <https://koreascience.kr/article/JAKO200806135603722.page?lang=ko>
- Jeu en bout de pale, étude complète : <https://core.ac.uk/download/357550149.pdf>
- ebm-papst DiaForce (diagonal) : <https://www.digikey.com/en/articles/high-performance-cooling-diagonal-compact-fans>
- DigiKey, rendements EC / PSC / pôles ombragés : <https://www.digikey.com/en/articles/ac-input-electronically-commutated-fans>
- TI MCF8316A : <https://www.ti.com/product/MCF8316A> ; MCF8316D : <https://www.ti.com/product/MCF8316D>
- Fortior FT8132 (fiche) : <https://shop.mev-elektronik.com/wp-content/uploads/FT8132Q.pdf>
