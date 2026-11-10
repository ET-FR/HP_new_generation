# Nomenclature : PAC de fenêtre réversible R290 (≈ 3,5 kW, pièce ≤ 50 m²)

Première version, 9 novembre 2026. Masses et coûts : **ordres de grandeur** (petite série,
hors main-d'œuvre), à remplacer par des devis. Charge R290 : part de la charge totale (cible ≤ 152 g).

Légende impact charge : **++** majeur, **+** notable, **–** négligeable.

## 1. Circuit frigorifique

| Élément | Rôle | Choix envisagé | Masse | Coût | Charge R290 |
|---|---|---|---|---|---|
| Compresseur | Comprime la vapeur | Rotatif BLDC R290, 16 cm³, 15 à 110 Hz | 8 à 10 kg | 80 à 150 € | **+** (huile : ≈ 40 g dissous) |
| Échangeur intérieur | Condenseur (chauffage) / évaporateur (clim) | Tube-ailettes, microcanaux ou impression 3D (étude CFD en cours) | 1 à 2 kg | 30 à 300 € (3D : à chiffrer) | **++** |
| Échangeur extérieur | Évaporateur (chauffage) / condenseur (clim) ; givre | Idem, contrainte de givrage | 1,5 à 3 kg | 40 à 400 € | **++** |
| Vanne 4 voies | Inverse le cycle (chauffage / clim / dégivrage) | Vanne à tiroir, bobine 230 V | 0,4 kg | 10 à 20 € | – |
| Détendeur électronique (EEV) | Règle le débit, surchauffe 5 K | Moteur pas à pas | 0,2 kg | 15 à 30 € | – |
| Accumulateur d'aspiration | Protège le compresseur du liquide (dégivrage, inversion) | Petit volume, ou supprimé si le compresseur le tolère | 0,3 kg | 5 à 10 € | **+** |
| Filtre déshydrateur | Humidité, particules | Bidirectionnel | 0,1 kg | 3 à 6 € | – |
| Silencieux de refoulement | Pulsations, bruit | Option | 0,2 kg | 3 à 5 € | – |
| Tuyauterie, brasures | Liaisons, traversée de fenêtre | Cuivre Ø 6 à 9 mm, longueurs minimales | 0,5 à 1 kg | 10 à 20 € | **+** (ligne liquide) |
| Vannes de service | Charge, contrôle | Schrader | – | 2 à 4 € | – |
| Huile | Lubrification compresseur | POE ou PAG compatible R290 | 0,25 à 0,3 kg | 3 € | **+** (solubilité) |
| Propane R290 | Fluide | ≤ 152 g | 0,15 kg | 2 € | – |

## 2. Capteurs et sécurité

| Élément | Rôle | Choix envisagé | Coût |
|---|---|---|---|
| Capteurs / pressostats HP et BP | Sécurité, régulation | Pressostat HP mécanique + capteurs de pression | 10 à 30 € |
| Sondes de température (×6) | Refoulement, aspiration, 2 échangeurs, air intérieur et extérieur | Thermistances CTN | 5 à 10 € |
| Détecteur de fuite R290 | Exigence IEC 60335-2-40 (unité intérieure) | Capteur infrarouge ou semi-conducteur | 15 à 40 € |
| Protection thermique compresseur | Surchauffe moteur | Intégrée ou externe | 2 à 5 € |

## 3. Électronique et commande

| Élément | Rôle | Choix envisagé | Coût |
|---|---|---|---|
| Variateur compresseur | Vitesse variable, rendement à charge partielle | Onduleur BLDC sans capteur + radiateur | 30 à 60 € |
| Carte de commande | Régulation, dégivrage, sécurités | Microcontrôleur | 10 à 25 € |
| Filtre CEM + correction du facteur de puissance | Conformité réseau | PFC actif | 10 à 20 € |
| Interface utilisateur | Consigne, modes | Télécommande + Wi-Fi / appli | 5 à 15 € |

## 4. Air et eau

| Élément | Rôle | Choix envisagé | Coût |
|---|---|---|---|
| Ventilateur intérieur | ≈ 500 m³/h, silencieux | Tangentiel ou centrifuge, moteur EC | 15 à 30 € |
| Ventilateur extérieur | ≈ 1 300 m³/h | Hélicoïde, moteur EC | 15 à 30 € |
| Volutes, gaines, grilles | Guidage de l'air, éviter la recirculation de l'air rejeté | Plastique injecté | 10 à 20 € |
| Filtre à air intérieur | Poussière, protection de l'échangeur | Lavable | 2 à 5 € |
| Bac à condensats + évacuation | Eau de condensation et de dégivrage | Pompe ou projection sur le condenseur | 5 à 15 € |
| Résistance antigel du bac | Dégivrage par grand froid | Option | 5 à 10 € |

## 5. Mécanique et intégration fenêtre

| Élément | Rôle | Choix envisagé | Coût |
|---|---|---|---|
| Carrosserie + cloison isolante | Séparer l'intérieur de l'extérieur, limiter les ponts thermiques | Tôle / plastique, mousse | 30 à 60 € |
| Kit fenêtre | Étanchéité à l'air et à l'eau | Deux versions : battant (UE), guillotine (USA) | 10 à 30 € |
| Antivibratoires + isolation acoustique | Bruit (critère majeur en chambre) | Silentblocs, capotage du compresseur | 5 à 15 € |
| Isolation des tuyaux froids | Condensation, pertes | Mousse élastomère | 2 à 5 € |

## Points critiques

| Sujet | Pourquoi |
|---|---|
| Charge ≤ 152 g | Échangeurs (volume interne) et huile dominent ; accumulateur et ligne liquide ensuite |
| Givre et condensats | Échangeur extérieur + bac + dégivrage : risque n° 1 des surfaces compactes |
| Bruit | Compresseur et ventilateurs à proximité du lit |
| Recirculation d'air extérieur | Rejet et aspiration côte à côte sur une fenêtre |
| Sécurité R290 | Détection de fuite, composants électriques non sources d'inflammation |
