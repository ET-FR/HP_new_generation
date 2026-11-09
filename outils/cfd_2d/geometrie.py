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
from shapely.geometry import Point, Polygon

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
}


def contour_interieur(forme: str, Dh: float = 4.0) -> Polygon:
    """Canal intérieur centré en (0, 0), mis à l'échelle pour avoir le diamètre hydraulique Dh."""
    p = FORMES[forme][1]()
    p = affinity.translate(p, -p.centroid.x, -p.centroid.y)
    k = Dh / (4 * p.area / p.length)      # Dh est proportionnel à la taille
    return affinity.scale(p, k, k, origin=(0, 0))


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
             pas_rond_sur_D=2.0, amont_D=5.0, aval_D=10.0) -> Batterie:
    """Batterie en quinconce respectant le critère d'équité (même section et périmètre intérieurs
    totaux par unité de surface frontale que la batterie de tubes ronds)."""
    inter = contour_interieur(forme, Dh)
    exter = inter.buffer(paroi, quad_segs=32, join_style="round")
    A_rond = math.pi * Dh ** 2 / 4
    D_ref = Dh + 2 * paroi                      # Ø extérieur du rond de référence
    Pt = pas_rond_sur_D * D_ref * inter.area / A_rond
    Pl = Pt * math.sqrt(3) / 2
    xmin, _, xmax, _ = exter.bounds
    x0 = -xmin                                  # le noyau commence au bord d'attaque du 1er rang
    centres = []
    for i in range(rangs):
        x = x0 + i * Pl
        centres.append((x, Pt / 2) if i % 2 == 0 else (x, 0.0))
    fin = x0 + (rangs - 1) * Pl + xmax
    return Batterie(forme, FORMES[forme][0], inter, exter, Pt, Pl, rangs, centres,
                    (0.0, fin), (-amont_D * D_ref, fin + aval_D * D_ref))


if __name__ == "__main__":
    print(f"{'forme':16s} {'A int':>7s} {'P int':>7s} {'Dh':>5s} {'P ext':>7s} {'Pt':>6s} {'Pl':>6s} {'noyau':>6s}")
    for f in FORMES:
        b = batterie(f)
        print(f"{f:16s} {b.A_int:7.2f} {b.P_int:7.2f} {4*b.A_int/b.P_int:5.2f} {b.P_ext:7.2f} "
              f"{b.Pt:6.2f} {b.Pl:6.2f} {b.x_noyau[1]:6.1f}")
