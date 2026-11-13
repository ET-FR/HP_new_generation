#!/usr/bin/env python3
"""
PDF « Pistes et idées » : rassemble les idées, les estimations et les schémas notés pendant l'étude
(lois de conception, théorie constructale, loi de Murray, biomimétisme, tubes parallèles à l'air,
charge de propane, distributeur, ventilateurs, ailettes, optimisation de forme).

Réutilise les pages et la mise en forme du rapport CFD (outils/cfd_2d/rapport_pdf.py) et les figures
de docs/figures/ et docs/maillages/.

    python conception_echangeur/outils/analytique/rapport_pistes.py      → docs/pistes_et_idees.pdf
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "outils" / "cfd_2d"))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.image as mpimg  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle, Wedge  # noqa: E402

import rapport_pdf as R  # noqa: E402

DOCS = RACINE / "docs"
SORTIE = DOCS / "pistes_et_idees.pdf"
A4, BLEU = R.A4, R.BLEU
GRIS, VERT, ORANGE, ROUGE, BLEU_C = "#495057", "#1baf7a", "#eb6834", "#c0392b", "#2a78d6"


def titre_page(fig, titre, sous_titre=""):
    fig.text(0.06, 0.965, titre, fontsize=15, fontweight="bold", color=BLEU)
    if sous_titre:
        fig.text(0.06, 0.945, sous_titre, fontsize=8.5, color=GRIS, va="top", linespacing=1.4)


def _replier(fig, texte, taille, largeur_fig):
    """Coupe le texte en lignes dont la largeur rendue tient dans largeur_fig (fraction de page)."""
    rendu = fig.canvas.get_renderer()
    mots = [m[i:i + 80] for m in texte.split() for i in range(0, len(m), 80)]   # coupe les très longues URL
    lignes, cour = [], ""
    sonde = fig.text(0, 0, "", fontsize=taille)
    for m in mots:
        essai = (cour + " " + m).strip()
        sonde.set_text(essai)
        if cour and sonde.get_window_extent(rendu).width / fig.bbox.width > largeur_fig:
            lignes.append(cour); cour = m
        else:
            cour = essai
    sonde.remove()
    return lignes + ([cour] if cour else []) or [""]


def paragraphe(fig, y, texte, taille=8.6, couleur="#212529", retrait=0.06, largeur=0.88, interligne=0.0155):
    """Texte replié à la largeur `largeur` (fraction de page) ; « • » en début de ligne = puce.
    Renvoie l'ordonnée sous le texte."""
    for bloc in texte.strip().split("\n"):
        puce = bloc.startswith("• ")
        x = retrait + (0.018 if puce else 0)
        for k, l in enumerate(_replier(fig, bloc[2:] if puce else bloc, taille, largeur - (x - retrait))):
            if puce and k == 0:
                fig.text(retrait + 0.004, y, "•", fontsize=taille, color=couleur, va="top")
            fig.text(x, y, l, fontsize=taille, color=couleur, va="top")
            y -= interligne * taille / 8.6
    return y - 0.006


def intertitre(fig, y, texte):
    fig.text(0.06, y, texte, fontsize=11, fontweight="bold", color=BLEU, va="top")
    return y - 0.027


def page_texte(pdf, titre, sous_titre, sections, conclusion=None):
    fig = plt.figure(figsize=A4)
    titre_page(fig, titre, sous_titre)
    y = 0.925 - 0.0165 * (sous_titre.count("\n") + 1) if sous_titre else 0.925
    for t, corps in sections:
        if t:
            y = intertitre(fig, y, t)
        if isinstance(corps, tuple):           # tableau : (entêtes, lignes, largeurs[, degrades])
            ent, lig, larg = corps[:3]
            y = R.tableau(fig, y + 0.03, ent, lig, larg, "", taille=7.6, h_ligne=0.022,
                          degrades=corps[3] if len(corps) > 3 else None) + 0.01
        else:
            y = paragraphe(fig, y, corps) - 0.01
    if conclusion:
        R.conclusion(fig, y, conclusion[1], conclusion[0])
    pdf.savefig(fig); plt.close(fig)


def page_figure(pdf, titre, image, texte="", sous_titre="", hauteur=0.55):
    """Une figure en haut de page, puis un texte d'explication."""
    fig = plt.figure(figsize=A4)
    titre_page(fig, titre, sous_titre)
    im = mpimg.imread(image)
    h_img, w_img = im.shape[:2]
    larg = 0.90
    haut = min(hauteur, larg * h_img / w_img * A4[0] / A4[1])
    ax = fig.add_axes([0.05, 0.93 - haut, larg, haut]); ax.imshow(im, interpolation="none"); ax.axis("off")
    if texte:
        paragraphe(fig, 0.93 - haut - 0.02, texte)
    pdf.savefig(fig); plt.close(fig)


# ------------------------------------------------------------------------------------------------
def page_couverture(pdf):
    fig = plt.figure(figsize=A4)
    fig.text(0.06, 0.90, "Pistes et idées", fontsize=26, fontweight="bold", color=BLEU)
    fig.text(0.06, 0.865, "PAC de fenêtre réversible au propane : échangeurs imprimés en 3D", fontsize=12,
             color=GRIS)
    fig.text(0.06, 0.845, f"Mis à jour le {date.today():%d/%m/%Y}. Compagnon de docs/resultats_cfd.pdf (résultats CFD).\n"
             "Détail et sources : docs/biomimetisme.md et docs/plan_formes_simples.md (section 10).",
             fontsize=8, color=GRIS, va="top", linespacing=1.4)
    y = intertitre(fig, 0.79, "Le constat qui oriente tout")
    y = paragraphe(fig, y, """
La charge de propane (152 g au plus, dont environ 95 g déjà pris par l'huile du compresseur, le carter et la ligne liquide) se joue d'abord sur la LONGUEUR de tube, puis sur le DIAMÈTRE INTÉRIEUR. En tubes nus à 1 m/s, il faut environ 450 m de tube et la limite est dépassée à tous les diamètres. Il faut donc à la fois des canaux fins et des tubes courts : les ailettes (étape 3) deviennent le chemin critique.
Ce document rassemble les idées notées en chemin, avec leur état : estimation, simple idée, ou à valider par calcul ou par essai.""")
    lignes = [
        ["Équation de conception (charge en une ligne)", "outil de tri", "estimation", "p. 2"],
        ["Charge selon le diamètre intérieur et les circuits", "côté propane", "estimation", "p. 3"],
        ["Théorie constructale (Bejan)", "méthode", "cadre", "p. 4"],
        ["Écart optimal entre ailettes ≈ 1,6 mm", "étape 3", "formule", "p. 4"],
        ["Collecteurs en arbre de Murray", "collecteurs", "estimation", "p. 5"],
        ["Distributeur imprimé à orifices calibrés", "étape 4", "idée", "p. 6"],
        ["Huit formes bio-inspirées", "étapes 3 à 5", "idées sourcées", "p. 7 et 8"],
        ["Ventilateurs : disque devant l'axial, anneau autour du centrifuge", "ventilateurs", "idée", "p. 9"],
        ["Tubes parallèles à l'air", "en attente", "à valider en CFD 3D", "p. 10"],
        ["Ailettes plates : premier maillage 3D", "étape 3", "prêt (calcul à lancer)", "p. 11"],
        ["Trouver la forme mathématiquement", "étape 4", "méthode", "p. 12"],
    ]
    y = R.tableau(fig, y - 0.005, ["Piste", "Où", "État", "Page"], lignes, [0.52, 0.16, 0.22, 0.10],
                  "Sommaire", taille=8, h_ligne=0.024)
    pdf.savefig(fig); plt.close(fig)


def page_equation(pdf):
    page_texte(pdf, "Équation de conception : la charge en une ligne",
               "Pour transférer Q avec un écart moyen ΔT, il faut une conductance UA = Q / ΔT. En écrivant la charge par mètre "
               "de tube\ndivisée par la conductance par mètre de tube, on obtient une formule qui montre tous les leviers.",
               [("charge  =  (Q / ΔT)  ×  ρ̄  ×  A_int  /  (h × η × P_air)", ""),
                ("Les leviers", (["Terme", "Sens", "Comment le réduire"],
                                 [["Q / ΔT", "conductance demandée", "ΔT plus grand (mais le COP baisse)"],
                                  ["ρ̄", "masse volumique moyenne du propane", "condenseur : c'est lui qui porte la charge"],
                                  ["A_int", "section intérieure du canal", "canal plus fin (Di²) ou plusieurs petits canaux"],
                                  ["h × η", "échange côté air × rendement d'ailette", "forme du tube, vitesse de l'air"],
                                  ["P_air", "surface côté air par mètre de tube", "ailettes, TPMS"]],
                                 [0.14, 0.40, 0.46])),
                ("Vérification sur notre cas", """
Tube rond de référence (Di 4 mm, h = 62 W/m²K, sans ailettes) : environ 1,7 g de propane par W/K au condenseur. Le condenseur demande environ 320 W/K, d'où environ 550 g ; le calcul détaillé de la page suivante trouve 618 g. La formule tient.
Le budget est d'environ 45 g pour le condenseur, soit environ 12 fois moins. Par exemple : canal de 4 à 2 mm (× 4) et ailettes avec un rendement réaliste (× 3 environ). Aucun levier seul ne suffit."""),
                ("Les bornes théoriques", """
• Écart optimal entre ailettes (Bejan et Sciubba) : D_opt ≈ 2,7 × L × Be^(-1/4). Profondeur 41,6 mm, perte de charge ≈ 5 Pa → D_opt ≈ 1,6 mm, l'écart du maillage préparé pour l'étape 3.
• Analogie de Reynolds : en laminaire, le rapport chaleur / frottement (j/f) a un plafond ; les plaques parallèles en sont proches. Il borne ce qu'on peut encore gagner sur le compromis chaleur / ventilation.""")],
               ("Usage proposé", ["Classer toutes nos configurations par grammes de propane par W/K, à P vent / Q donné.",
                                  "Servir de fonction objectif rapide pour l'optimisation de l'étape 4."]))


def page_constructale(pdf):
    page_figure(pdf, "Théorie constructale (Bejan, 1996)", DOCS / "figures" / "theorie_constructale.png", """
Loi constructale : un système de taille finie traversé par un flux évolue vers la forme qui fait passer ce flux de plus en plus facilement. La méthode utile pour l'ingénieur : optimiser le plus petit élément, assembler, optimiser à nouveau à chaque échelle ; le résultat est presque toujours un arbre.
• Résultats connus : écart optimal entre plaques ou ailettes (notre 1,6 mm), poumons (environ 23 niveaux de ramification retrouvés en 2004), loi de Murray comme cas particulier.
• Critique : la loi est très générale et difficile à réfuter ; la méthode, elle, donne des résultats vérifiables. On s'en sert comme méthode de conception.
• La méthode n'impose aucune forme ; la formule de l'écart entre ailettes est établie pour des plaques parallèles, d'autres formules existent pour les cylindres et les picots.
• Pour notre PAC : une optimisation par échelle (ailette, tube et circuit, collecteur, batterie), puis vérification sur le cycle complet (COP, charge ≤ 152 g).""", hauteur=0.58)


def page_murray(pdf):
    fig = plt.figure(figsize=A4)
    titre_page(fig, "Collecteurs en arbre de Murray", "À reprendre lors de la conception des collecteurs.")
    im = mpimg.imread(DOCS / "figures" / "loi_murray.png")
    h = 0.92 * im.shape[0] / im.shape[1] * A4[0] / A4[1]
    ax = fig.add_axes([0.04, 0.925 - h, 0.92, h])
    ax.imshow(im, interpolation="none"); ax.axis("off")
    y = paragraphe(fig, 0.91 - h, """
Loi de Murray (1926) : dans un réseau qui se ramifie, pompage et volume sont minimaux ensemble quand, à chaque division, r₀³ = r₁³ + r₂³ (deux branches égales : parent = 1,26 × enfant). Le frottement à la paroi est alors le même dans tous les canaux.
• Forme : la loi vaut pour toute forme de canal gardée semblable d'un niveau à l'autre (goutte, losange…). Si seule la largeur varie à hauteur fixe, elle devient linéaire (w₀ = w₁ + w₂). À section égale, le rond frotte le moins (carré + 13 %, ellipse 2:1 + 25 %, triangle + 38 %).
• Impression 3D : un canal rond horizontal de plus de 6 à 8 mm a besoin de supports ; forme en goutte (pointe en haut), autoportante, pour quelques % de perte de charge en plus.
• Elle ne maximise pas la surface d'échange : c'est un outil de distribution. Côté propane, la surface n'est pas limitante (h ≈ 2 000 à 5 000 W/m²K contre ≈ 60 côté air).""")
    lignes = [["Arbre de Murray 6,35 → 2 mm", "7,9 cm³", "3,6 g", "0,5 g", "0,1 à 0,3 g"],
              ["Collecteur droit classique Ø 8 mm", "15,1 cm³", "6,9 g", "0,9 g", "0,2 à 0,5 g"]]
    y = R.tableau(fig, y - 0.005, ["32 circuits, face de 30 cm", "Volume", "Liquide 46 °C", "Entrée évaporateur",
                                   "Vapeur"], lignes, [0.34, 0.13, 0.16, 0.20, 0.17],
                  "Ordres de grandeur", taille=7.6, h_ligne=0.024)
    R.conclusion(fig, y + 0.01, [
        "Le volume gagné est modeste (≈ 3 g par collecteur côté liquide) face aux tubes (40 à 150 g).",
        "Le vrai intérêt est la répartition : chaque circuit a exactement le même chemin, alors qu'un collecteur droit",
        "    répartit mal le mélange liquide / vapeur entre 20 à 40 circuits.",
        "PAC réversible : l'arbre doit marcher dans les deux sens (petit côté liquide, répartition égale côté mélange).",
        "En diphasique l'exposant de la loi change : à recalculer avec le modèle de charge."], "À retenir")
    pdf.savefig(fig); plt.close(fig)


def page_distributeur(pdf):
    page_texte(pdf, "Détente et répartition : le distributeur imprimé",
               "Question de départ : l'échangeur peut-il servir de détendeur, avec plusieurs entrées qui donnent des Δp "
               "différents selon la demande ?",
               [("Ce qui ne marche pas : détendre dans l'échangeur", """
La température du propane suit sa pression. Si la pression baisse progressivement le long de l'évaporateur, son début reste à 30 ou 40 °C et chauffe l'air au lieu de le refroidir : on perd une bonne partie de la surface, justement ce qui coûte en charge. C'est pourquoi la détente se fait en un point, juste avant l'évaporateur."""),
                ("Ce qui existe déjà", (["Solution", "Principe", "Limite"],
                                        [["Tube capillaire", "tube fin et long, détendeur fixe", "ne s'adapte pas à la demande"],
                                         ["Rampe d'orifices", "plusieurs orifices + électrovannes", "réglage par paliers, plus cher"],
                                         ["Détendeur électronique", "une vanne pilotée, 10 à 20 €", "réglage continu, réversible"]],
                                        [0.26, 0.40, 0.34])),
                ("La piste retenue", """
Avec 20 à 40 circuits en parallèle (estimation de charge), imprimer un orifice calibré à l'entrée de chaque circuit : il assure la répartition égale et une partie de la détente, comme dans les évaporateurs à microcanaux. On garde un détendeur électronique en amont pour la surchauffe et l'inversion de cycle. Effet attendu : répartition égale, et collecteur d'entrée en mélange léger plutôt qu'en liquide dense."""),
                ("Idées voisines à chiffrer au même moment", """
• Échangeur interne ligne liquide / aspiration : quelques % de COP selon la littérature pour le propane, intégrable à l'impression.
• Éjecteur : récupère l'énergie de la détente ; ≈ 3 à 5 % de COP pour le propane, difficile à régler à faible puissance.""")],
               ("À évaluer", ["Étape 4, dans le modèle de la machine, avec le volume des collecteurs en arbre de Murray."]))


def page_biomimetisme_tableau(pdf):
    page_texte(pdf, "Biomimétisme : ce qu'on retient",
               "Recherche bibliographique rapide (résumés d'articles, souvent un seul groupe) : à lire en détail avant "
               "d'engager des calculs.\nLa nature résout séparément trois de nos problèmes : distribuer, échanger, "
               "évacuer l'eau.",
               [("Les pistes et leur étape", (["Forme naturelle", "Idée pour nous", "Chiffres publiés", "Où"],
                  [["Moustache de phoque", "tube elliptique ondulé", "- 13 % Δp, - 4,5 % échange", "étape 3"],
                   ["Nageoire de baleine", "ailette à bord d'attaque ondulé", "aucune étude trouvée", "étape 3"],
                   ["Vaisseaux, bronches", "collecteur en arbre de Murray", "parent = 1,26 × enfant", "collecteurs"],
                   ["Poumon d'oiseau, thon", "circuits à contre-courant global", "principe connu", "étape 4"],
                   ["Oreille d'éléphant", "canaux de propane dans l'ailette", "aucune étude trouvée", "étape 4"],
                   ["Toile d'araignée, tournesol", "échangeur en disque ou en anneau", "études sur puces", "ventilateurs"],
                   ["Aile de chouette", "pale à bord de fuite dentelé", "- 2 dB, + 4,7 % de débit", "ventilateur"],
                   ["Scarabée du Namib, Nepenthes", "mouillabilité alternée", "+ 16 % en givrage", "étape 5"],
                   ["Branchies", "écart optimal des lamelles", "même logique que Bejan", "étape 3"],
                   ["Papillon (gyroïde)", "surface TPMS déjà au plan", "", "étape 3"]],
                  [0.25, 0.34, 0.26, 0.15])),
                ("Les deux pistes les plus fortes", """
• Tube « moustache de phoque » : notre problème exact (tubes en travers qui lâchent des tourbillons). En essais sur des picots, 13 % de perte de charge en moins pour 4,5 % d'échange en moins face à un picot elliptique, ou ≈ 9 % de performance en plus à Δp égal. Demande la CFD 3D.
• Mouillabilité alternée : l'humidité est la cause n° 1 d'échec des essais réels ; surface en épines hydrophile / hydrophobe : + 16 % d'échange en givrage ; surface alternée : jusqu'à + 76 % d'eau évacuée ; revêtement super-hydrophobe : Δp humide presque divisée par 2.""")])


def page_ventilateurs(pdf):
    fig = plt.figure(figsize=A4)
    titre_page(fig, "Ventilateurs et forme de la batterie",
               "Choix de la nomenclature (docs/nomenclature.md) : intérieur tangentiel ou centrifuge (≈ 500 m³/h, "
               "silencieux),\nextérieur hélicoïde axial (≈ 1 300 m³/h). Le ventilateur n'est pas encore choisi.")
    # schémas
    ax = fig.add_axes([0.05, 0.56, 0.42, 0.33]); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Rectangle((-0.6, -2.2), 0.4, 4.4, fc="#d3d8de", ec="#5b6570"))
    for k in range(9):
        ax.add_patch(Circle((-0.4, -1.9 + k * 0.48), 0.09, fc=ROUGE, ec="none"))
    ax.add_patch(Rectangle((0.6, -0.25), 0.5, 0.5, fc="#5b6570"))
    for s in (1, -1):
        ax.add_patch(Wedge((0.85, 0), 1.9, 90 * s - 14, 90 * s + 14, width=1.6, fc="#9aa5b1", ec="#5b6570"))
    for yv in (-1.5, 0, 1.5):
        ax.add_patch(FancyArrowPatch((-2.2, yv), (-0.8, yv), arrowstyle="-|>", mutation_scale=12, color=BLEU_C))
    ax.text(-2.3, 2.6, "Extérieur : axial", fontsize=10, fontweight="bold", color=BLEU)
    ax.text(-2.3, -2.9, "batterie en disque devant l'hélice\n(toile d'araignée, tournesol)", fontsize=8, color=GRIS,
            va="top")
    ax.set_xlim(-2.5, 3.0); ax.set_ylim(-3.6, 3.0)
    ax = fig.add_axes([0.53, 0.56, 0.42, 0.33]); ax.set_aspect("equal"); ax.axis("off")
    ax.add_patch(Circle((0, 0), 2.0, fc="#d3d8de", ec="#5b6570"))
    ax.add_patch(Circle((0, 0), 1.55, fc="white", ec="#5b6570"))
    import math
    for k in range(28):
        a = 2 * math.pi * k / 28
        ax.add_patch(Circle((1.78 * math.cos(a), 1.78 * math.sin(a)), 0.07, fc=ROUGE, ec="none"))
    for k in range(18):
        a = 2 * math.pi * k / 18
        ax.plot([0.45 * math.cos(a), 1.2 * math.cos(a + 0.35)], [0.45 * math.sin(a), 1.2 * math.sin(a + 0.35)],
                color="#5b6570", lw=1.4)
    for k in range(8):
        a = 2 * math.pi * k / 8 + 0.2
        ax.add_patch(FancyArrowPatch((2.1 * math.cos(a), 2.1 * math.sin(a)), (2.9 * math.cos(a), 2.9 * math.sin(a)),
                                     arrowstyle="-|>", mutation_scale=11, color=BLEU_C))
    ax.text(-3.0, 2.7, "Intérieur : centrifuge", fontsize=10, fontweight="bold", color=BLEU)
    ax.text(-3.0, -3.0, "batterie en anneau autour de la roue,\nl'air la traverse vers l'extérieur", fontsize=8,
            color=GRIS, va="top")
    ax.set_xlim(-3.2, 3.2); ax.set_ylim(-3.7, 3.0)
    y = paragraphe(fig, 0.53, """
• Extérieur, axial : la batterie en disque devant l'hélice épouse le jet rond du ventilateur ; distribution du propane en rayons et en cercles (toile d'araignée), tubes possibles en spirale (tournesol). C'est la batterie la plus importante pour la charge : en climatisation elle est condenseur et porte près de 90 % du propane des tubes.
• Intérieur, centrifuge : l'air sort tout autour de la roue ; la forme naturelle est un anneau que l'air traverse du centre vers l'extérieur. L'air ralentit en s'éloignant du centre (la surface de passage augmente) : effet à étudier sur l'échange.
• Intérieur, tangentiel (splits muraux) : batterie classique en V inversé autour du ventilateur ; la piste disque ne s'applique pas, les tubes ondulés, les ailettes et les collecteurs en arbre restent valables.
• Bruit : pales inspirées de la chouette (bord de fuite dentelé, - 2 dB et + 4,7 % de débit publiés) ; attention, certains bords d'attaque modifiés font perdre du débit. Le bruit compte surtout à l'intérieur.
• Simulateur : l'exemple de ventilateur réel (ebm-papst W1G200, axial 200 mm) sort des courbes avec notre circuit d'air ; le choix reste à faire.""")
    pdf.savefig(fig); plt.close(fig)


def page_ailettes(pdf):
    info = json.loads((DOCS / "maillages" / "ailettes_plates.json").read_text())
    n3d = f"{info['cellules_3d']:,}".replace(",", " ")
    page_figure(pdf, "Étape 3 : ailettes plates, premier maillage 3D", DOCS / "maillages" / "ailettes_plates.png", f"""
But : savoir si des ailettes plates sur nos meilleurs tubes donnent un meilleur compromis chaleur / ventilation que les tubes nus à charge égale. Les ailettes sont en métal plein : elles ajoutent de la surface côté air (× {info['facteur_surface']:.1f}) sans propane, et raccourcissent les tubes, ce qui est le levier principal de la charge.
• Maillage : le maillage 2D à couches validé, empilé en {info['tranches']} tranches entre deux ailettes ({n3d} mailles). Pas {info['pas_ailettes_mm']:g} mm, épaisseur {info['epaisseur_mm']:g} mm, ailettes sur toute la profondeur ({info['profondeur_ailettes_mm']:.1f} mm = 4 Pl).
• Durée estimée : écoulement probablement stable entre ailettes serrées → 5 à 10 min par cas sur 48 cœurs ; s'il oscille, 1 à 3 h par cas.
• Avant le calcul : resserrer le maillage aux bords d'attaque et de fuite de l'ailette, convergence en z (20, 28, 40 tranches), rendement d'ailette réel (conduction) ensuite.
• Variantes notées : ellipse 2:1, pas de 2,5 mm (batterie extérieure qui givre), bord d'attaque ondulé.""", hauteur=0.50)


def page_optimisation(pdf):
    page_texte(pdf, "Trouver la forme mathématiquement",
               "Problème : maximiser la chaleur échangée à puissance de ventilation, charge et profondeur données, sous "
               "les équations\nde l'écoulement et de la chaleur. L'inconnue est la paroi elle-même.",
               [("Ce qu'on sait déjà", """
• Corps de traînée minimale (Pironneau, 1973) : la forme exacte est connue en écoulement très lent ; il existe des formes optimales démontrables.
• Synergie des champs (Guo) : l'échange est maximal quand l'air pousse dans le sens du gradient de température.
• Le décollement coûte en perte de charge sans échanger : arrière effilé, avant arrondi.
• Renouveler la couche limite : plusieurs petites surfaces en série valent mieux qu'une grande (h ∝ 1/√D en laminaire).
Nos résultats vont dans ce sens : ellipse 2:1 et lentille sur le front de Pareto, carré et faces plates loin."""),
                ("Les méthodes", (["Méthode", "Principe", "Coût"],
                                  [["Paramétrique + bayésienne", "5 à 10 paramètres, l'algorithme choisit les cas",
                                    "50 à 200 cas 2D"],
                                   ["Adjointe", "sensibilité en chaque point de la paroi", "20 à 50 couples de calculs"],
                                   ["Topologique", "chaque maille : air ou métal", "lourd, écoulement stable"]],
                                  [0.27, 0.48, 0.25])),
                ("Difficulté propre à notre cas", """
À 1 m/s nos écoulements 2D oscillent ; l'adjoint et la topologie supposent en général un écoulement stable. Deux issues : travailler à 0,5 m/s (Re ≈ 400, intéressant d'après l'étape 1b), ou avec ailettes (écoulement probablement stable). OpenFOAM v2606 contient un solveur adjoint, à vérifier pour l'échange de chaleur.""")],
               ("Ordre proposé", ["1. Famille de formes paramétrée (rond, ellipses et lentille comme cas particuliers), "
                                  "optimisée en 2D à charge égale.",
                                  "2. Adjoint pour affiner les meilleures formes. 3. Topologie plus tard, en 3D avec ailettes."]))


def page_sources(pdf):
    sources = []
    for l in (DOCS / "biomimetisme.md").read_text().split("## Sources")[1].splitlines():
        if l.startswith("* "):
            sources.append(l[2:].strip())
        elif l.startswith("  ") and sources:          # suite d'une entrée sur plusieurs lignes
            sources[-1] += " " + l.strip()
    fig = plt.figure(figsize=A4)
    titre_page(fig, "Sources", "Liens de la recherche bibliographique (détail dans docs/biomimetisme.md).")
    y = 0.92
    for s in sources:
        y = paragraphe(fig, y, "• " + s, taille=7.2, interligne=0.0145)
        if y < 0.05:
            pdf.savefig(fig); plt.close(fig)
            fig = plt.figure(figsize=A4); titre_page(fig, "Sources (suite)"); y = 0.92
    pdf.savefig(fig); plt.close(fig)


def main():
    with PdfPages(SORTIE) as pdf:
        page_couverture(pdf)                                                    # p. 1
        page_equation(pdf)                                                      # p. 2
        R.page_charge_propane(pdf)                                              # p. 3
        page_constructale(pdf)                                                  # p. 4
        page_murray(pdf)                                                        # p. 5
        page_distributeur(pdf)                                                  # p. 6
        page_figure(pdf, "Les formes bio-inspirées", DOCS / "figures" / "formes_biomimetisme.png",
                    "Schémas de principe, pas des géométries dimensionnées. En vert : l'étape où reprendre chaque piste.",
                    hauteur=0.60)                                               # p. 7
        page_biomimetisme_tableau(pdf)                                          # p. 8
        page_ventilateurs(pdf)                                                  # p. 9
        R.page_longitudinal(pdf)                                                # p. 10
        page_ailettes(pdf)                                                      # p. 11
        page_optimisation(pdf)                                                  # p. 12
        page_sources(pdf)
    R.compresser(SORTIE)
    print(SORTIE)


if __name__ == "__main__":
    main()
