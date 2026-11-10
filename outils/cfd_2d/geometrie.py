"""
Formes de tubes et batteries 2D pour l'étude des formes simples côté air.

Règles (docs/plan_formes_simples.md) :
  * même charge de propane et même périmètre de contact côté propane par unité de surface
    frontale  =>  même diamètre hydraulique intérieur Dh = 4 A / P pour toutes les formes ;
  * paroi d'épaisseur constante (contour extérieur = contour intérieur décalé) ;
  * batterie en quinconce, 4 rangs ; pas transversal du rond = 2 Ø extérieur, et pour les
    autres formes pas multiplié par A_forme / A_rond (même section totale par unité de face).

Unités : mm. L'air s'écoule selon +x.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

N_PTS = 240  # points par contour


def _cercle(r=1.0):
    t = np.linspace(0, 2 * math.pi, N_PTS, endpoint=False)
    return Polygon(np.c_[r * np.cos(t), r * np.sin(t)])


def _ellipse(rapport):
    t = np.linspace(0, 2 * math.pi, N_PTS, endpoint=False)
    return Polygon(np.c_[rapport * np.cos(t), np.sin(t)])     # grand axe selon x (sens de l'air)


def _goutte(rapport=3.0):
    """Nez rond en amont, queue effilée en aval ; longueur totale = rapport × largeur."""
    r = 1.0
    L = rapport * 2 * r          # du bord d'attaque à la pointe
    xc = -L / 2 + r              # centre du nez
    xp = L / 2                   # pointe
    d = xp - xc
    a = math.acos(r / d)         # angle du point de tangence
    t = np.linspace(a, 2 * math.pi - a, N_PTS - 1)
    arc = np.c_[xc + r * np.cos(t), r * np.sin(t)]
    return Polygon(np.vstack([arc, [[xp, 0.0]]]))


def _lentille(rapport=3.0):
    """Intersection de deux disques : profil symétrique pointu aux deux bouts (type tube UMD)."""
    L, W = rapport, 1.0          # demi-longueur et demi-largeur
    R = (L * L + W * W) / (2 * W)
    haut = Point(0, W - R).buffer(R, quad_segs=N_PTS // 4)
    bas = Point(0, R - W).buffer(R, quad_segs=N_PTS // 4)
    return haut.intersection(bas)


def _rect(rapport):
    return Polygon([(-rapport, -1), (rapport, -1), (rapport, 1), (-rapport, 1)])


def _triangle(pointe_amont: bool):
    # triangle équilatéral, une pointe sur l'axe x
    s = 1.0
    pts = [(s * math.cos(a), s * math.sin(a)) for a in (0, 2 * math.pi / 3, 4 * math.pi / 3)]
    p = Polygon(pts)                      # pointe vers +x (aval) : base face à l'air
    return affinity.rotate(p, 180, origin=(0, 0)) if pointe_amont else p


def _naca(epaisseur=0.30, n=200):
    """Profil NACA 00xx symétrique (bord de fuite fermé), corde 1, bord d'attaque en amont (x < 0)."""
    b = np.linspace(0, math.pi, n)
    x = 0.5 * (1 - np.cos(b))                       # resserrement aux bords d'attaque et de fuite
    yt = 5 * epaisseur * (0.2969 * np.sqrt(x) - 0.1260 * x - 0.3516 * x ** 2 + 0.2843 * x ** 3 - 0.1036 * x ** 4)
    haut = np.c_[x, yt][::-1]
    bas = np.c_[x, -yt][1:-1]
    return Polygon(np.vstack([haut, bas]))


def _stade(rapport):
    """Tube plat aux bouts arrondis (forme des tubes microcanaux), longueur / épaisseur = rapport."""
    a = rapport - 1.0
    return LineString([(-a, 0), (a, 0)]).buffer(1.0, quad_segs=N_PTS // 8)


def _hexagone(pointe_amont: bool):
    a0 = 0.0 if pointe_amont else math.pi / 6
    return Polygon([(math.cos(a0 + k * math.pi / 3), math.sin(a0 + k * math.pi / 3)) for k in range(6)])


def _demi_cercle(plat_amont: bool):
    """Demi-disque : côté plat face à l'air (plat_amont) ou côté arrondi face à l'air."""
    t = np.linspace(-math.pi / 2, math.pi / 2, N_PTS // 2)
    p = Polygon(np.c_[np.cos(t), np.sin(t)])         # côté plat à gauche (amont)
    return p if plat_amont else affinity.rotate(p, 180, origin=(0, 0))


def _trois_canaux():
    """Trois canaux ronds Ø 1 côte à côte dans le sens de l'air (tube multicanaux)."""
    return MultiPolygon([Point(x, 0).buffer(0.5, quad_segs=N_PTS // 4) for x in (-1.25, 0.0, 1.25)])


# Contours extérieurs particuliers (sinon : contour intérieur décalé de l'épaisseur de paroi).
# Fonctions (intérieur mis à l'échelle, paroi en mm) -> contour extérieur, en mm.
def _ext_etoile(inter, paroi, n=6, longueur=2.0, epaisseur=1.0):
    """Tube rond + n ailettes longitudinales radiales (épaisseur 1 mm, bout arrondi)."""
    R = math.sqrt(inter.area / math.pi) + paroi
    ailettes = [LineString([(0, 0), ((R + longueur) * math.cos(a), (R + longueur) * math.sin(a))])
                .buffer(epaisseur / 2, quad_segs=16) for a in np.arange(n) * 2 * math.pi / n]
    forme = unary_union([Point(0, 0).buffer(R, quad_segs=64)] + ailettes)
    return forme.buffer(0.6, quad_segs=16).buffer(-0.6, quad_segs=16)   # congés de 0,6 mm aux pieds


def _ext_cannele(inter, paroi, n=12, amplitude=0.4):
    """Contour extérieur ondulé : rayon R + a + a cos(n θ) ; paroi minimale = paroi (creux)."""
    R = math.sqrt(inter.area / math.pi) + paroi
    t = np.linspace(0, 2 * math.pi, 720, endpoint=False)
    r = R + amplitude + amplitude * np.cos(n * t)
    return Polygon(np.c_[r * np.cos(t), r * np.sin(t)])


def _ext_multicanaux(inter, paroi):
    """Enveloppe en stade autour des canaux, paroi minimale = paroi."""
    xs = sorted(g.centroid.x for g in inter.geoms)
    r = max(math.sqrt(g.area / math.pi) for g in inter.geoms) + paroi
    return LineString([(xs[0], 0), (xs[-1], 0)]).buffer(r, quad_segs=N_PTS // 8)


EXTERIEURS = {"etoile6": _ext_etoile, "cannele12": _ext_cannele, "trois_canaux": _ext_multicanaux}


FORMES = {
    "rond": ("Rond", lambda: _cercle()),
    "carre": ("Carré", lambda: _rect(1.0)),
    "losange": ("Losange (carré à 45°)", lambda: affinity.rotate(_rect(1.0), 45, origin=(0, 0))),
    "triangle_pointe": ("Triangle, pointe face à l'air", lambda: _triangle(True)),
    "triangle_base": ("Triangle, base face à l'air", lambda: _triangle(False)),
    "ellipse2": ("Ellipse 2:1", lambda: _ellipse(2.0)),
    "ellipse3": ("Ellipse 3:1", lambda: _ellipse(3.0)),
    "plat4": ("Tube plat 4:1", lambda: _rect(4.0)),
    "goutte": ("Goutte d'eau 3:1", lambda: _goutte(3.0)),
    "lentille": ("Lentille 3:1", lambda: _lentille(3.0)),
    # série 2 (9 novembre 2026)
    "naca0030": ("Profil d'aile NACA 0030", lambda: _naca(0.30)),
    "goutte_inversee": ("Goutte inversée (pointe face à l'air)", lambda: affinity.rotate(_goutte(3.0), 180, origin=(0, 0))),
    "ellipse4": ("Ellipse 4:1", lambda: _ellipse(4.0)),
    "ellipse5": ("Ellipse 5:1", lambda: _ellipse(5.0)),
    "stade8": ("Tube plat 8:1 bouts arrondis", lambda: _stade(8.0)),
    "hexagone_pointe": ("Hexagone, pointe face à l'air", lambda: _hexagone(True)),
    "hexagone_plat": ("Hexagone, plat face à l'air", lambda: _hexagone(False)),
    "demi_cercle_plat": ("Demi-cercle, plat face à l'air", lambda: _demi_cercle(True)),
    "demi_cercle_rond": ("Demi-cercle, arrondi face à l'air", lambda: _demi_cercle(False)),
    "etoile6": ("Tube rond à 6 ailettes longitudinales", lambda: _cercle()),
    "cannele12": ("Tube rond cannelé (12 ondes)", lambda: _cercle()),
    "trois_canaux": ("Tube multicanaux (3 canaux)", lambda: _trois_canaux()),
}


def contour_interieur(forme: str, Dh: float = 4.0) -> Polygon:
    """Canal intérieur centré en (0, 0), mis à l'échelle pour avoir le diamètre hydraulique Dh."""
    p = FORMES[forme][1]()
    p = affinity.translate(p, -p.centroid.x, -p.centroid.y)
    k = Dh / (4 * p.area / p.length)      # Dh est proportionnel à la taille
    return affinity.scale(p, k, k, origin=(0, 0))


def ecart_min(b) -> float:
    """Plus petit passage d'air entre deux tubes (mm), images périodiques comprises."""
    tubes = []
    for cx, cy in b.centres:
        for dy in (-b.Pt, 0.0, b.Pt):
            tubes.append(affinity.translate(b.exterieur, cx, cy + dy))
    d = math.inf
    for i in range(len(tubes)):
        for j in range(i + 1, len(tubes)):
            if tubes[i].distance(tubes[j]) > 0 or tubes[i].intersects(tubes[j]):
                d = min(d, tubes[i].distance(tubes[j]))
    return d


@dataclass
class Batterie:
    forme: str
    nom: str
    interieur: Polygon
    exterieur: Polygon
    Pt: float          # pas transversal (hauteur du domaine périodique)
    Pl: float          # pas longitudinal
    rangs: int
    centres: list      # (x, y) des tubes dans le domaine [0, Pt] (y = 0 répété en y = Pt)
    x_noyau: tuple     # début et fin du noyau
    x_domaine: tuple   # début et fin du domaine

    @property
    def A_int(self):
        return self.interieur.area

    @property
    def P_int(self):
        return self.interieur.length

    @property
    def P_ext(self):
        return self.exterieur.length


def batterie(forme: str, Dh: float = 4.0, paroi: float = 1.0, rangs: int = 4,
             pas_rond_sur_D=2.0, amont_D=5.0, aval_D=10.0, pt_facteur=1.0, pl_facteur=1.0,
             aligne=False) -> Batterie:
    """Batterie respectant le critère d'équité (même section et périmètre intérieurs totaux par
    unité de surface frontale que la batterie de tubes ronds), en quinconce par défaut.
    Niveau 2 : pt_facteur et pl_facteur multiplient les pas de référence (la charge par m² de face
    varie alors comme rangs / pt_facteur) ; aligne=True met tous les tubes sur la même ligne."""
    inter = contour_interieur(forme, Dh)
    if forme in EXTERIEURS:
        exter = EXTERIEURS[forme](inter, paroi)
    else:
        exter = inter.buffer(paroi, quad_segs=32, join_style="round")
    A_rond = math.pi * Dh ** 2 / 4
    D_ref = Dh + 2 * paroi                      # Ø extérieur du rond de référence
    Pt0 = pas_rond_sur_D * D_ref * inter.area / A_rond
    Pt = pt_facteur * Pt0
    Pl = pl_facteur * Pt0 * math.sqrt(3) / 2
    xmin, _, xmax, _ = exter.bounds
    x0 = -xmin                                  # le noyau commence au bord d'attaque du 1er rang
    centres = []
    for i in range(rangs):
        x = x0 + i * Pl
        centres.append((x, Pt / 2) if (i % 2 == 0 or aligne) else (x, 0.0))
    fin = x0 + (rangs - 1) * Pl + xmax
    return Batterie(forme, FORMES[forme][0], inter, exter, Pt, Pl, rangs, centres,
                    (0.0, fin), (-amont_D * D_ref, fin + aval_D * D_ref))


if __name__ == "__main__":
    print(f"{'forme':16s} {'A int':>7s} {'P int':>7s} {'Dh':>5s} {'P ext':>7s} {'Pt':>6s} {'Pl':>6s} {'noyau':>6s}")
    for f in FORMES:
        b = batterie(f)
        print(f"{f:16s} {b.A_int:7.2f} {b.P_int:7.2f} {4*b.A_int/b.P_int:5.2f} {b.P_ext:7.2f} "
              f"{b.Pt:6.2f} {b.Pl:6.2f} {b.x_noyau[1]:6.1f}")
