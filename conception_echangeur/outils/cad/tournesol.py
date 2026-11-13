"""Géométrie du dernier niveau en tournesol (sans FreeCAD, testable seul) :
* positions des tubes selon le modèle de Vogel (angle d'or, r² réparti uniformément dans l'anneau) ;
* attribution de deux tubes à chaque nœud du niveau précédent (affectation optimale, méthode hongroise) ;
* trajets des branches du dernier niveau (glissement latéral en Y doux).
  Les longueurs diffèrent de quelques mm (≈ 1 % d'un circuit complet) : on ne les égalise pas. L'essai
  d'allongement par une bosse latérale faisait se croiser les branches (0,8 mm entre axes).
Tous les points sont des tuples (x, y, z) en mm.

    .venv/bin/python conception_echangeur/outils/cad/tournesol.py   → contrôle rapide (écarts, longueurs, croisements)
"""
import math

ANGLE_OR = math.pi * (3 - math.sqrt(5))  # 137,5°


def vogel(n, r_min, r_max, th0=0.0):
    """n points en tournesol dans l'anneau r_min..r_max (aires égales par point)."""
    return [(math.sqrt(r_min ** 2 + (i + 0.5) * (r_max ** 2 - r_min ** 2) / n), th0 + i * ANGLE_OR)
            for i in range(n)]


def hongrois(cout):
    """Affectation de coût minimal (matrice carrée), O(n³). Renvoie col[i] attribuée à la ligne i."""
    n = len(cout)
    INF = float("inf")
    u, v, p, voie = [0.0] * (n + 1), [0.0] * (n + 1), [0] * (n + 1), [0] * (n + 1)
    for i in range(1, n + 1):
        p[0], j0 = i, 0
        mini, vu = [INF] * (n + 1), [False] * (n + 1)
        while True:
            vu[j0] = True
            i0, delta, j1 = p[j0], INF, 0
            for j in range(1, n + 1):
                if not vu[j]:
                    c = cout[i0 - 1][j - 1] - u[i0] - v[j]
                    if c < mini[j]:
                        mini[j], voie[j] = c, j0
                    if mini[j] < delta:
                        delta, j1 = mini[j], j
            for j in range(n + 1):
                if vu[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    mini[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = voie[j0]
            p[j0] = p[j1]
            j0 = j1
    res = [0] * n
    for j in range(1, n + 1):
        res[p[j] - 1] = j - 1
    return res


def feuilles_tournesol(noeuds_xy, r_min, r_max, pas_rotation_deg=1.0):
    """Place 2 × len(noeuds) tubes en tournesol et attribue deux tubes à chaque nœud.
    La rotation du motif est choisie pour minimiser la somme des distances² nœud → tube.
    Renvoie (liste de paires [(x, y), (x, y)] dans l'ordre des nœuds, rotation retenue en degrés)."""
    m = len(noeuds_xy)
    meilleur = None
    for k in range(int(round(360 / pas_rotation_deg))):
        th0 = math.radians(k * pas_rotation_deg)
        pts = [(r * math.cos(t), r * math.sin(t)) for r, t in vogel(2 * m, r_min, r_max, th0)]
        cout = [[(pts[j][0] - noeuds_xy[i // 2][0]) ** 2 + (pts[j][1] - noeuds_xy[i // 2][1]) ** 2
                 for j in range(2 * m)] for i in range(2 * m)]
        aff = hongrois(cout)
        total = sum(cout[i][aff[i]] for i in range(2 * m))
        if meilleur is None or total < meilleur[0]:
            meilleur = (total, k * pas_rotation_deg, [pts[aff[i]] for i in range(2 * m)])
    _, rot, ordre = meilleur
    return [(ordre[2 * i], ordre[2 * i + 1]) for i in range(m)], rot


def y_doux(t):
    lisse = t * t * (3 - 2 * t)
    return 0.5 * (1 - (1 - t) ** 2) + 0.5 * lisse


def trajet(a, b, z_a, z_b, n=32):
    """Points d'une branche du nœud a (x, y) au tube b (x, y) : glissement latéral en Y doux, z linéaire."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    return [(a[0] + dx * y_doux(i / n), a[1] + dy * y_doux(i / n), z_a + (z_b - z_a) * i / n) for i in range(n + 1)]


def longueur(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def branches(paires, noeuds_xy, z_a, z_b):
    """Trajets du dernier niveau, dans l'ordre nœud 0 (tube a, tube b), nœud 1, …"""
    return [{"noeud": nd, "feuille": f, "points": trajet(nd, f, z_a, z_b)}
            for pr, nd in zip(paires, noeuds_xy) for f in pr]


def distance_min_entre_branches(branches, exclure_debut=0.35):
    """Plus petite distance entre les axes de deux branches de nœuds différents, ou entre deux sœurs
    au-delà de la fraction exclure_debut du trajet (elles partent du même nœud)."""
    dmin = float("inf")
    for i, a in enumerate(branches):
        for j in range(i + 1, len(branches)):
            b = branches[j]
            soeurs = a["noeud"] == b["noeud"]
            pa = a["points"][int(len(a["points"]) * exclure_debut):] if soeurs else a["points"]
            pb = b["points"][int(len(b["points"]) * exclure_debut):] if soeurs else b["points"]
            for p in pa:
                for q in pb:
                    d = math.dist(p, q)
                    if d < dmin:
                        dmin = d
    return dmin


if __name__ == "__main__":
    # Contrôle avec les nœuds du niveau 4 du modèle à 16 tubes (couronne R 32,5)
    R = 32.5
    th = {(0, 0): 0.0}
    for k in range(1, 5):
        for j in range(2 ** k):
            th[(k, j)] = j * math.pi if k == 1 else th[(k - 1, j // 2)] + (-1 if j % 2 == 0 else 1) * math.pi / 2 ** k
    noeuds = [(R * math.cos(th[(4, j)]), R * math.sin(th[(4, j)])) for j in range(16)]
    paires, rot = feuilles_tournesol(noeuds, 19.0, 46.0)
    tubes = [f for pr in paires for f in pr]
    dmin = min(math.dist(a, b) for i, a in enumerate(tubes) for b in tubes[i + 1:])
    br = branches(paires, noeuds, 0.0, 20.0)
    lg = [longueur(b["points"]) for b in br]
    print(f"rotation {rot}°, écart min entre axes des tubes {dmin:.2f} mm")
    print(f"longueur des branches {min(lg):.1f} à {max(lg):.1f} mm")
    print(f"distance min entre axes de branches : {distance_min_entre_branches(br):.2f} mm")
