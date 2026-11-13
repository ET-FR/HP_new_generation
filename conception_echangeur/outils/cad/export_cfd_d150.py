"""Surfaces du domaine d'air de l'échangeur Ø 150 pour snappyHexMesh, une par zone de conditions aux limites.

Lit docs/formes/cylindre_d150_helice/echangeur_d150.FCStd (objets domaine_air, ailette) et dimensions.json,
classe chaque face du domaine d'air :
  entree   face plane au bout du conduit d'entrée (y = −longueur du conduit)
  sortie   face plane au bout du conduit de sortie
  tubes    cylindres de rayon = Ø ext. des tubes / 2
  ailette  faces posées sur l'ailette hélicoïdale ou ses remplissages
  parois   le reste (tube principal, fonds, noyau, parois des conduits)
et écrit <zone>.stl en MÈTRES dans docs/formes/cylindre_d150_helice/cfd/ (+ zones.json : aires, nombre de faces).

    flatpak run --command=FreeCADCmd org.freecad.FreeCAD -c \
      "exec(open('/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur/outils/cad/export_cfd_d150.py').read())"
"""
import json
import math
import os

import FreeCAD as App
import Mesh
import MeshPart
import Part

RACINE = "/home/thomas/Documents/PROJETCS/HP_new_generation/conception_echangeur"
D = os.path.join(RACINE, "docs/formes/cylindre_d150_helice")
SORTIE = os.path.join(D, "cfd")
FINESSE = {"tubes": (0.01, 0.15), "ailette": (0.05, 0.2), "parois": (0.05, 0.2), "entree": (0.1, 0.3), "sortie": (0.1, 0.3)}


def main():
    os.makedirs(SORTIE, exist_ok=True)
    dim = json.load(open(os.path.join(D, "dimensions.json")))
    p = dim["parametres"]
    Ld, rt = p["conduit_long"], p["od_tube"] / 2
    Ri, Rc = dim["rayons_mm"]["interieur"], dim["rayons_mm"]["noyau"]
    th = math.radians(dim["helice"]["tours"] * 360.0)
    t_sortie = App.Vector(-math.sin(th), math.cos(th), 0)
    doc = App.openDocument(os.path.join(D, "echangeur_d150.FCStd"))
    air = doc.getObject("domaine_air").Shape
    ailette = doc.getObject("ailette").Shape
    zones = {k: [] for k in ("entree", "sortie", "tubes", "ailette", "parois")}
    for fa in air.Faces:
        s = fa.Surface
        c = fa.CenterOfMass
        nom = None
        if isinstance(s, Part.Plane):
            n = s.Axis
            if abs(c.y + Ld) < 0.05 and abs(abs(n.y) - 1) < 1e-4:
                nom = "entree"
            elif abs(c.dot(t_sortie) - Ld) < 0.05 and abs(abs(n.dot(t_sortie)) - 1) < 1e-4:
                nom = "sortie"
        elif isinstance(s, Part.Cylinder) and abs(s.Radius - rt) < 1e-6:
            nom = "tubes"
        elif isinstance(s, Part.Cylinder) and min(abs(s.Radius - Ri), abs(s.Radius - Rc)) < 1e-6 and abs(abs(s.Axis.z) - 1) < 1e-6:
            nom = "parois"      # paroi du tube principal ou noyau (l'ailette d'un bloc les touche aussi)
        if nom is None and not isinstance(s, Part.Plane):
            # surface de balayage posée sur la paroi (r = Ri) ou le noyau (r = Rc) : points de la face tous à ce rayon
            pts, _ = fa.tessellate(2.0)
            rr = [math.hypot(q.x, q.y) for q in pts]
            if rr and (max(abs(r - Ri) for r in rr) < 0.05 or max(abs(r - Rc) for r in rr) < 0.05):
                nom = "parois"
        if nom is None:
            # point SUR la face (le centre de masse d'une hélicoïde est près de l'axe, hors de la face)
            u0, u1, v0, v1 = fa.ParameterRange
            q = fa.valueAt((u0 + u1) / 2, (v0 + v1) / 2)
            if not fa.isInside(q, 1e-3, True):
                q = fa.Vertexes[0].Point.add((fa.Vertexes[-1].Point - fa.Vertexes[0].Point) * 0.5)
            nom = "ailette" if ailette.distToShape(Part.Vertex(q))[0] < 1e-3 else "parois"
        zones[nom].append(fa)
    bilan = {}
    for nom, faces in zones.items():
        if not faces:
            raise RuntimeError(f"zone vide : {nom}")
        lin, ang = FINESSE[nom]
        m = Mesh.Mesh()
        for fa in faces:   # triangulation directe face par face (meshFromShape plantait FreeCAD sur une face plane)
            g = fa.copy()
            g.scale(1e-3)
            if isinstance(fa.Surface, Part.Plane):     # plan : triangulation directe (meshFromShape plantait)
                pts, tris = g.tessellate(lin * 1e-3)
                m.addFacets([[pts[a], pts[b], pts[c]] for a, b, c in tris])
            else:                                       # surfaces courbes : mailleur standard
                m.addMesh(MeshPart.meshFromShape(Shape=g, LinearDeflection=lin * 1e-3, AngularDeflection=ang))
        f = os.path.join(SORTIE, f"{nom}.stl")
        m.write(f)
        # nom du solide = nom de la zone (snappyHexMesh nomme le patch d'après le fichier)
        bilan[nom] = dict(faces_cao=len(faces), facettes=m.CountFacets, aire_m2=round(sum(x.Area for x in faces) * 1e-6, 5))
        print(nom, bilan[nom], flush=True)
    bilan["aire_totale_m2"] = round(air.Area * 1e-6, 5)
    json.dump(bilan, open(os.path.join(SORTIE, "zones.json"), "w"), indent=1)


main()
