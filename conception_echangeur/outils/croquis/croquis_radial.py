"""Croquis 2D à l'échelle de l'échangeur cylindrique à flux radial (idée du 12/11/2026).

Cylindre couché Ø 200 × 400 mm. Paroi = échangeur plissé en accordéon (étoile). Ventilateur tangentiel dans la
chambre centrale : il aspire l'air à travers la paroi sur ≈ 280°, le rejette par un secteur libre à gauche, dans
une volute qui remonte et sort vers la droite au-dessus du cylindre (dessin de l'utilisateur).

    .venv/bin/python conception_echangeur/outils/croquis/croquis_radial.py
    → docs/formes/cylindre_radial/croquis_2d.html
"""
import math
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs/formes/cylindre_radial/croquis_2d.html"

# --- hypothèses (mm, m³/h) ---
R_EXT, R_INT, R_ROT = 100.0, 65.0, 50.0       # paroi plissée de 35 mm, rotor tangentiel Ø 100
L = 400.0                                      # choix utilisateur : Ø 200 × 400
SECT = (140.0, 220.0)                          # secteur de sortie (degrés, 0 = droite, sens trigo)
PAS_PLI = 12.0                                 # un pli tous les 12° (sommet extérieur tous les 12°)
H_SORTIE = 170.0                               # hauteur de la bouche de sortie
Y_INT = 150.0                                  # paroi intérieure de la volute au-dessus du cylindre
DEBITS = (2500, 2000, 1500)
R_FILTRE = 108.0                               # A : manchon filtrant autour du cylindre
PLI_FILTRE = 3.0                               # B : filtre plissé dans la bouche, surface × 3


def pol(r, a):
    a = math.radians(a)
    return r * math.cos(a), r * math.sin(a)


def f(x, n=0):
    return f"{x:,.{n}f}".replace(",", " ").replace(".", ",")


def plis():
    """Ligne brisée des plis dans le secteur d'aspiration, et longueur développée."""
    a0, a1 = SECT[1], SECT[0] + 360
    n = int((a1 - a0) / (PAS_PLI / 2))
    pts = []
    for i in range(n + 1):
        a = a0 + i * (a1 - a0) / n
        pts.append(pol(R_EXT - 3 if i % 2 == 0 else R_INT + 3, a))
    long_dev = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
    return pts, long_dev, (a1 - a0)


def coupe(variante="A"):
    """SVG de la coupe transversale (échelle 1 mm = 1,6 px).
    A : volute de refoulement au-dessus, aspiration à travers l'échangeur (dessin du 12/11).
    B : la même coupe retournée, volute d'aspiration en dessous, l'air sort à travers l'échangeur."""
    k = 1.6
    C = variante in ("C", "A2")                # ventilateur simple dans la volute, chambre vide (A2 : version de A)
    B = variante in ("B", "C")
    X = lambda x: x * k
    Y = lambda y: (y if B else -y) * k
    P = lambda p: f"{X(p[0]):.1f},{Y(p[1]):.1f}"
    s = []

    def fleche(p1, p2, cls, mk):
        """Flèche de p1 vers p2 (variante A) ; inversée et recolorée en variante B."""
        if B:
            p1, p2 = p2, p1
            cls = {"air-froid": "air-chaud", "air-chaud": "air-froid", "air-froid fin": "air-chaud fin"}[cls]
            mk = {"fb": "fr", "fr": "fb"}[mk]
        s.append(f'<line x1="{X(p1[0])}" y1="{Y(p1[1])}" x2="{X(p2[0])}" y2="{Y(p2[1])}" class="{cls}" marker-end="url(#{mk})"/>')
    # paroi de la volute (extérieure et intérieure) : du bord du secteur de sortie jusqu'à la bouche à droite
    o0, i0 = pol(R_EXT, SECT[1]), pol(R_EXT, SECT[0])
    y_haut = Y_INT + H_SORTIE
    ext = (f"M{P(o0)} C{P((-190, -75))} {P((-235, 170))} {P((-130, 275))} "
           f"Q{P((-95, y_haut))} {P((-20, y_haut))} L{P((95, y_haut))}")
    intr = f"M{P(i0)} C{P((-100, 110))} {P((-95, Y_INT))} {P((-35, Y_INT))} L{P((95, Y_INT))}"
    s.append(f'<path d="{ext}" class="mur"/><path d="{intr}" class="mur"/>')
    s.append(f'<line x1="{X(95)}" y1="{Y(Y_INT)}" x2="{X(95)}" y2="{Y(y_haut)}" class="bouche"/>')
    # cloisons du passage de sortie (du rotor à la paroi) : bec (langue) et paroi arrière
    for a, nom in ((SECT[0], "bec"), (SECT[1], "paroi arrière")):
        p1, p2 = pol(R_INT if C else R_ROT + 3, a), pol(R_EXT, a)
        s.append(f'<line x1="{X(p1[0])}" y1="{Y(p1[1])}" x2="{X(p2[0])}" y2="{Y(p2[1])}" class="mur"/>')
    # contour de l'enveloppe (grille de protection) dans le secteur d'aspiration
    a0, a1 = math.radians(SECT[1]), math.radians(SECT[0] + 360)
    g0, g1 = pol(R_EXT + 2, SECT[1]), pol(R_EXT + 2, SECT[0])
    s.append(f'<path d="M{P(g0)} A{X(R_EXT + 2)},{X(R_EXT + 2)} 0 1 {1 if B else 0} {P(g1)}" class="grille"/>')
    # filtre : A = manchon amovible autour du cylindre (secteur d'aspiration) ; B = cartouche plissée dans la bouche
    if B:
        zz = []
        n = 14
        for i in range(n + 1):
            yy = Y_INT + 8 + i * (H_SORTIE - 16) / n
            zz.append((95 - (28 if i % 2 else 4), yy))
        s.append('<polyline points="' + " ".join(P(q) for q in zz) + '" class="filtre"/>')
        s.append(f'<text x="{X(60)}" y="{Y(Y_INT + H_SORTIE + 12)}" class="txt" text-anchor="middle">filtre plissé</text>')
    else:
        f0, f1 = pol(R_FILTRE, SECT[1] + 3), pol(R_FILTRE, SECT[0] - 3)
        s.append(f'<path d="M{P(f0)} A{X(R_FILTRE)},{X(R_FILTRE)} 0 1 {1 if B else 0} {P(f1)}" class="filtre"/>')
        s.append(f'<text x="{X(118)}" y="{Y(28)}" class="txt">filtre (manchon amovible)</text>')
    # plis
    pts, long_dev, sect = plis()
    s.append('<polyline points="' + " ".join(P(p) for p in pts) + '" class="pli"/>')
    if C:
        # ventilateur axial juste après le filtre (axe horizontal, souffle vers la gauche)
        x0, x1, ya, yb = 22.0, 46.0, Y_INT + 4, Y_INT + H_SORTIE - 4
        s.append(f'<rect x="{X(x0)}" y="{min(Y(ya), Y(yb))}" width="{X(x1 - x0)}" height="{abs(Y(yb) - Y(ya))}" class="ventilo"/>')
        ym = (ya + yb) / 2
        s.append(f'<rect x="{X(x0 + 6)}" y="{Y(ym) - X(14)}" width="{X(12)}" height="{X(28)}" class="moyeu"/>')
        for d in (-1, 1):
            s.append(f'<path d="M{P((x0 + 12, ym + d * 14))} L{P((x0 + 4, ym + d * 70))} L{P((x0 + 20, ym + d * 74))} Z" class="pale"/>')
        s.append(f'<text x="{X((x0 + x1) / 2)}" y="{Y(Y_INT + H_SORTIE + 12)}" class="txt" text-anchor="middle">ventilateur</text>')
        # répartiteur perforé (option) dans la chambre, utile quand l'air y entre en jet (variante C)
        if B:
            s.append(f'<circle cx="0" cy="0" r="{X(R_INT - 8)}" class="repartiteur"/>')
        s.append(f'<text x="{X(10)}" y="{Y(-35)}" class="txt" text-anchor="middle">chambre vide</text>')
        if B:
            s.append(f'<text x="{X(25)}" y="{Y(-118)}" class="txt">répartiteur perforé (option), pointillés</text>')
    rotor = not C
    if rotor:
        s.append(f'<circle cx="0" cy="0" r="{X(R_ROT)}" class="rotor"/>')
    for i in (range(30) if rotor else ()):
        a = i * 12
        p1, p2, p3 = pol(R_ROT - 9, a), pol(R_ROT - 4, a - 4), pol(R_ROT, a - 10)
        s.append(f'<path d="M{P(p1)} Q{P(p2)} {P(p3)}" class="aube"/>')
    if rotor:
        s.append(f'<circle cx="0" cy="0" r="{X(8)}" class="axe"/>')
    # sens de rotation (horaire : la gauche monte, l'air sort vers le haut de la volute)
    r_f = R_ROT - 20
    d0, d1 = pol(r_f, 60), pol(r_f, -30)
    if rotor and not B:     # en B, le sens dépend de la position du bec (à étudier)
        s.append(f'<path d="M{P(d0)} A{X(r_f)},{X(r_f)} 0 0 1 {P(d1)}" class="rotation" marker-end="url(#fn)"/>')
    # flèches d'aspiration (bleu) : radiales dans le secteur d'aspiration, y compris sous la volute
    for a in range(int(SECT[1]) + 15, int(SECT[0]) + 360 - 5, 22):
        if 50 < (a % 360) < 135:   # sous la volute : l'air arrive par la droite, entre volute et cylindre
            continue
        fleche(pol(R_EXT + 38, a), pol(R_EXT + 8, a), "air-froid", "fb")
    for a in (65, 90, 115):
        fleche(pol(R_EXT + 30, a), pol(R_EXT + 8, a), "air-froid", "fb")
    fleche((150, 118), (112, 118), "air-froid", "fb")
    # dans la chambre : vers le rotor
    for a in (300, 0, 40, 250):
        fleche(pol(R_INT - 3, a), pol((R_INT - 30) if C else (R_ROT + 5), a), "air-froid fin", "fb")
    # air rejeté (rouge) : passage de sortie, volute, bouche
    if B:
        trajet = f"M{P((60, 235))} L{P((-80, 225))} C{P((-170, 200))} {P((-185, 50))} {P((-120, 20))} L{P((-35 if not C else -20, 0))}"
        s.append(f'<path d="{trajet}" class="air-froid" marker-end="url(#fb)"/>')
    else:
        trajet = f"M{P((-35 if not C else -20, 0))} L{P((-120, 20))} C{P((-185, 50))} {P((-170, 200))} {P((-80, 225))} L{P((60, 235))}"
        s.append(f'<path d="{trajet}" class="air-chaud" marker-end="url(#fr)"/>')
    for yy in (Y_INT + 30, Y_INT + 75, Y_INT + 140):
        fleche((100, yy), (150, yy), "air-chaud", "fr")
    # cotes
    c = 'class="cote"'
    s.append(f'<line x1="{X(-R_EXT)}" y1="{Y(-R_EXT - 30)}" x2="{X(R_EXT)}" y2="{Y(-R_EXT - 30)}" {c} marker-start="url(#fc)" marker-end="url(#fc)"/>'
             f'<text x="0" y="{Y(-R_EXT - 30) - 6}" class="txt" text-anchor="middle">Ø {f(2 * R_EXT)}</text>')
    p_e, p_i = pol(R_EXT, 300), pol(R_INT, 300)
    s.append(f'<line x1="{X(p_e[0])}" y1="{Y(p_e[1])}" x2="{X(p_i[0])}" y2="{Y(p_i[1])}" {c}/>'
             f'<text x="{X(p_e[0]) + 8}" y="{Y(p_e[1]) + 16}" class="txt">plis : {f(R_EXT - R_INT)} mm</text>')
    if rotor:
        s.append(f'<text x="0" y="{Y(-14)}" class="txt" text-anchor="middle">rotor Ø {f(2 * R_ROT)}</text>')
    t0, t1 = pol(R_EXT, SECT[0]), pol(R_EXT, SECT[1])
    gorge = math.dist(t0, t1)
    s.append(f'<text x="{X(-R_EXT) - 8}" y="{Y(0) + 4}" class="txt" text-anchor="end">gorge {f(gorge)} mm</text>')
    s.append(f'<line x1="{X(110)}" y1="{Y(Y_INT)}" x2="{X(110)}" y2="{Y(Y_INT + H_SORTIE)}" {c} marker-start="url(#fc)" marker-end="url(#fc)"/>'
             f'<text x="{X(118)}" y="{Y(Y_INT + H_SORTIE / 2) - 22}" class="txt">bouche {f(H_SORTIE)}</text>')
    if rotor:
        s.append(f'<text x="{X(-128)}" y="{Y(-58)}" class="txt">paroi arrière</text>')
        s.append(f'<text x="{X(-72)}" y="{Y(84)}" class="txt">bec</text>')
    s.append(f'<text x="{X(-250)}" y="{Y(150)}" class="txt" text-anchor="end">volute</text>')
    s.append(f'<text x="{X(118)}" y="{Y(-62)}" class="txt">échangeur plissé</text>')
    s.append(f'<text x="{X(20)}" y="{Y(Y_INT - 18) + (12 if B else 0)}" class="txt">{"sortie" if B else "aspiration"} entre volute et cylindre</text>')
    y_min, y_max = -R_EXT - 60, Y_INT + H_SORTIE + 25
    vb = f"{X(-300)} {min(Y(y_min), Y(y_max))} {X(600)} {X(y_max - y_min)}"
    return s, vb, gorge, long_dev, sect


# --- variante D (dessin de l'utilisateur du 12/11) : appareil en selle sous l'ouvrant, soufflage par le haut ---
D_COL = 150.0            # largeur du col de la cheminée (sur le cylindre), où loge le ventilateur
D_LARG = 50.0            # largeur de la fente de sortie (choix utilisateur : 50 × 400)
D_Y_COL, D_Y_EVA, D_Y_SORTIE = 195.0, 250.0, 285.0     # haut du col, fin du convergent, sortie
D_ARCS = ((300.0, 45.0 + 360), (135.0, 240.0))         # secteurs d'échangeur (droite, gauche) ; bas fermé = bac
D_BAC = (-80.0, 80.0, -97.0, -128.0)                   # x0, x1, haut, fond du bac à condensats
D_VITRE = -235.0


def plis_arc(a0, a1, re=R_EXT, ri=R_INT, pas=PAS_PLI):
    n = int(round((a1 - a0) / (pas / 2)))
    pts = [pol(re - 3 if i % 2 == 0 else ri + 3, a0 + i * (a1 - a0) / n) for i in range(n + 1)]
    return pts, sum(math.dist(pts[i], pts[i + 1]) for i in range(n))


def coupe_d():
    """Coupe de la variante D (1 mm = 1,6 px) : cylindre aspirant sur deux secteurs, bas fermé au-dessus du bac,
    cheminée verticale avec ventilateur axial (axe vertical) et volet de sortie, pont sous l'ouvrant de la fenêtre."""
    k = 1.6
    X = lambda x: x * k
    Y = lambda y: -y * k
    P = lambda p: f"{X(p[0]):.1f},{Y(p[1]):.1f}"
    s = []

    def ligne(p1, p2, cls, extra=""):
        s.append(f'<line x1="{X(p1[0]):.1f}" y1="{Y(p1[1]):.1f}" x2="{X(p2[0]):.1f}" y2="{Y(p2[1]):.1f}" class="{cls}" {extra}/>')

    def fleche(p1, p2, cls="air-froid", mk="fb"):
        ligne(p1, p2, cls, f'marker-end="url(#{mk})"')

    # vitre (ouvrant baissé) et pont en selle qui passe dessous
    s.append(f'<rect x="{X(D_VITRE - 9)}" y="{Y(330)}" width="{X(18)}" height="{X(330 - (-60))}" rx="6" class="vitre"/>')
    x0b, x1b, yh, yf = D_BAC
    s.append(f'<path d="M{P((-340, -78))} L{P((x0b - 6, -78))} Q{P((x0b, -78))} {P((x0b, -90))} L{P((x0b, yh))}" class="mur"/>')
    s.append(f'<path d="M{P((-340, -150))} L{P((x0b, yf - 8))} L{P((x1b, yf))} L{P((x1b, yh))}" class="mur"/>')
    # eau du bac (pente vers le pont)
    s.append(f'<path d="M{P((x0b + 2, yf - 3))} L{P((x1b - 2, yf + 4))} L{P((x1b - 2, yf + 9))} L{P((x0b + 2, yf + 4))} Z" class="eau"/>')
    fleche((-120, -138), (-300, -147), "eau-f", "fe")
    # bas du cylindre fermé (gouttière) entre les deux secteurs d'échangeur
    g0, g1 = pol(R_EXT, 240), pol(R_EXT, 300)
    s.append(f'<path d="M{P(g0)} A{X(R_EXT)},{X(R_EXT)} 0 0 0 {P(g1)}" class="mur"/>')
    # cheminée : col, évasement, sortie ; ventilateur ; volet
    xc = D_COL / 2
    yb = math.sqrt(R_EXT ** 2 - xc ** 2)
    for sg in (-1, 1):
        s.append(f'<path d="M{P((sg * xc, yb))} L{P((sg * xc, D_Y_COL))} Q{P((sg * xc, D_Y_EVA - 15))} {P((sg * D_LARG / 2, D_Y_EVA))} '
                 f'L{P((sg * D_LARG / 2, D_Y_SORTIE))}" class="mur"/>')
    yv = 150.0
    s.append(f'<rect x="{X(-D_COL / 2 + 2)}" y="{Y(yv + 3)}" width="{X(D_COL - 4)}" height="{X(6)}" class="ventilo"/>')
    s.append(f'<rect x="{X(-16)}" y="{Y(yv + 20)}" width="{X(32)}" height="{X(26)}" rx="3" class="moyeu"/>')
    for sg in (-1, 1):
        s.append(f'<path d="M{P((sg * 16, yv + 10))} L{P((sg * 68, yv + 3))} L{P((sg * 66, yv + 14))} Z" class="pale"/>')
    # volet : plein = clim (vertical), pointillé = chauffage (incliné vers la pièce, à droite)
    for xv in (-12, 12):
        ligne((xv, D_Y_SORTIE - 22), (xv, D_Y_SORTIE + 8), "volet")
        ligne((xv - 12, D_Y_SORTIE - 20), (xv + 12, D_Y_SORTIE + 8), "volet-ch")
    s.append(f'<line x1="{X(-D_LARG / 2)}" y1="{Y(D_Y_SORTIE + 8)}" x2="{X(D_LARG / 2)}" y2="{Y(D_Y_SORTIE + 8)}" class="bouche"/>')
    # grille, filtre et plis sur les deux secteurs
    surf = 0.0
    for a0, a1 in D_ARCS:
        q0, q1 = pol(R_EXT + 2, a0), pol(R_EXT + 2, a1)
        s.append(f'<path d="M{P(q0)} A{X(R_EXT + 2)},{X(R_EXT + 2)} 0 0 0 {P(q1)}" class="grille"/>')
        f0, f1 = pol(R_FILTRE, a0 + 2), pol(R_FILTRE, a1 - 2)
        s.append(f'<path d="M{P(f0)} A{X(R_FILTRE)},{X(R_FILTRE)} 0 0 0 {P(f1)}" class="filtre"/>')
        pts, ld = plis_arc(a0, a1)
        surf += ld
        s.append('<polyline points="' + " ".join(P(p) for p in pts) + '" class="pli"/>')
        for a in (0, 1):
            ligne(pol(R_INT, (a0, a1)[a]), pol(R_EXT, (a0, a1)[a]), "mur")       # cloisons de bout de galette
    # air : aspiré (bleu) sur les deux secteurs, rassemblé dans la chambre, soufflé (rouge) vers le haut
    for a in list(range(-50, 40, 18)) + list(range(146, 236, 18)):
        fleche(pol(R_EXT + 40, a), pol(R_EXT + 9, a))
    for a in (200, 250, 290, 340):
        fleche(pol(R_INT - 4, a), pol(R_INT - 32, a), "air-froid fin")
    for xx in (-35, 0, 35):
        fleche((xx, 10), (xx, 95), "air-chaud", "fr")
    for xx in (-12, 12):
        fleche((xx, D_Y_SORTIE + 14), (xx, D_Y_SORTIE + 55), "air-chaud", "fr")
    fleche((20, D_Y_SORTIE + 14), (55, D_Y_SORTIE + 45), "air-chaud pointe", "fr")
    # textes
    t = lambda x, y, txt, a="start": s.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" class="txt" text-anchor="{a}">{txt}</text>')
    t(D_VITRE, 340, "vitre (ouvrant baissé)", "middle")
    t(-330, -70, "pont en selle sous l'ouvrant (tubes, condensat)")
    t(-330, -172, "vers l'extérieur : condensat par gravité")
    t(0, -145, "bac à condensats (bas fermé sur 60°)", "middle")
    t(0, 20, "chambre vide", "middle")
    t(D_COL / 2 + 8, yv + 4, "ventilateur (axe vertical)")
    t(D_LARG / 2 + 30, D_Y_SORTIE - 8, "volet : plein = clim, pointillé = chauffage")
    t(D_COL / 2 + 8, (yv + yb) / 2 - 15, f"col {f(D_COL)} mm")
    t(D_COL / 2 + 8, (D_Y_COL + D_Y_EVA) / 2, "convergent")
    t(D_LARG / 2 + 30, D_Y_SORTIE + 25, f"fente de sortie {f(D_LARG)} × {f(L)} mm")
    t(R_EXT + 30, -70, "échangeur plissé + filtre")
    t(R_EXT + 45, 60, "côté pièce →")
    # cotes
    c = 'class="cote" marker-start="url(#fc)" marker-end="url(#fc)"'
    s.append(f'<line x1="{X(-R_EXT)}" y1="{Y(-R_EXT - 78)}" x2="{X(R_EXT)}" y2="{Y(-R_EXT - 78)}" {c}/>')
    t(0, -R_EXT - 72, f"Ø {f(2 * R_EXT)}", "middle")
    vb = f"{X(-345)} {Y(360)} {X(345 + 350)} {X(360 + 195)}"
    return s, vb, surf, sum(a1 - a0 for a0, a1 in D_ARCS)


# --- variante E (dessin de l'utilisateur du 12/11, vue de dessus) : tube cintré en fer à cheval autour de la fente ---
# repère du plan : x perpendiculaire à la vitre (0 = vitre, vers la pièce), y le long de la vitre ; z vertical (axe du tube à z = 0)
E_LARG = 400.0     # hors tout le long de la vitre (choix utilisateur)
E_RE, E_RI = 50.0, 32.0    # tube Ø 100 (choix utilisateur), plis de 18 mm
E_PAS = 36.0       # un pli tous les 36° (la galette de 8 mm doit tenir au fond du pli, r = 32)
E_RF = 55.0        # filtre
E_YC = E_LARG / 2 - E_RE   # ligne moyenne des branches : y = ±E_YC
E_PROF = 250.0     # profondeur hors tout dans la pièce (choix utilisateur)
E_HAUT = 200.0     # hauteur hors tout (choix utilisateur)
E_RK = 100.0       # rayon de cintrage de la ligne moyenne
E_XR = E_PROF - E_RE - E_RK   # longueur droite des branches (ligne moyenne), depuis la vitre
E_SECT = (300.0, 500.0)    # secteur d'échangeur dans la coupe du tube (0 = vers l'extérieur, 90 = haut)
E_SORTIE_TUBE = (140.0, 220.0)   # face du tube ouverte vers le plénum
E_Z_BAS = -E_RE - 15       # fond du bac côté vitre (axe du tube à z = 0)
E_Z_HAUT = E_Z_BAS + E_HAUT      # dessus de l'appareil = plan de la bouche
E_DV = 140.0               # ventilateur axial à axe vertical dans le plénum
E_ZV = E_RE + 35           # plan du ventilateur

def morceaux_e():
    """Morceaux de la ligne moyenne : ('d', longueur) droit ou ('c', angle en rad) cintré de rayon E_RK."""
    return [("d", E_XR), ("c", math.pi / 2), ("d", 2 * (E_YC - E_RK)), ("c", math.pi / 2), ("d", E_XR)]


def surfaces_e():
    """Surface de galette (développée × chemin parcouru par chaque segment, cintres compris), filtre, sortie du tube."""
    pts, _ = plis_arc(*E_SECT, E_RE, E_RI, E_PAS)
    a_gal = 0.0
    for kind, v in morceaux_e():
        for i in range(len(pts) - 1):
            (u0, z0), (u1, z1) = pts[i], pts[i + 1]
            a_gal += math.dist(pts[i], pts[i + 1]) * (v if kind == "d" else v * (E_RK + (u0 + u1) / 2))
    a_fil, n = 0.0, 200
    ouv = math.radians(E_SECT[1] - E_SECT[0] - 4)
    for kind, v in morceaux_e():
        for i in range(n):
            ph = math.radians(E_SECT[0] + 2) + ouv * (i + 0.5) / n
            a_fil += E_RF * ouv / n * (v if kind == "d" else v * (E_RK + E_RF * math.cos(ph)))
    corde = math.dist(pol(E_RE, E_SORTIE_TUBE[0]), pol(E_RE, E_SORTIE_TUBE[1]))
    u_s = E_RE * math.cos(math.radians(E_SORTIE_TUBE[0]))
    lg_int = sum(v if k == "d" else v * (E_RK + u_s) for k, v in morceaux_e())
    lg = sum(v if k == "d" else v * E_RK for k, v in morceaux_e())
    ri = E_RK - E_RE                                   # rayon des coins du plénum
    a_bouche = (E_XR + ri) * 2 * (E_YC - E_RE) - 2 * (ri ** 2 - math.pi * ri ** 2 / 4)
    return a_gal * 1e-6, a_fil * 1e-6, corde * lg_int * 1e-6, lg, a_bouche * 1e-6


def chemin_e(d, X, Y):
    """Ligne décalée de d (d > 0 : vers l'extérieur du fer à cheval), de la vitre en haut à la vitre en bas."""
    yk = E_YC - E_RK
    r = E_RK + d
    P = lambda x, y: f"{X(x):.1f},{Y(y):.1f}"
    return (f"M{P(0, E_YC + d)} L{P(E_XR, E_YC + d)} A{X(r):.1f},{X(r):.1f} 0 0 1 {P(E_XR + r, yk)} "
            f"L{P(E_XR + r, -yk)} A{X(r):.1f},{X(r):.1f} 0 0 1 {P(E_XR, -E_YC - d)} L{P(0, -E_YC - d)}")


def vue_dessus_e():
    k = 1.6
    X = lambda x: x * k
    Y = lambda y: -y * k
    s = []
    t = lambda x, y, txt, a="start": s.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" class="txt" text-anchor="{a}">{txt}</text>')

    def fleche(p1, p2, cls="air-froid", mk="fb"):
        s.append(f'<line x1="{X(p1[0]):.1f}" y1="{Y(p1[1]):.1f}" x2="{X(p2[0]):.1f}" y2="{Y(p2[1]):.1f}" class="{cls}" marker-end="url(#{mk})"/>')
    ye = E_YC + E_RE
    xo = E_XR + E_RK + E_RE
    s.append(f'<rect x="{X(-14)}" y="{Y(ye + 40)}" width="{X(11)}" height="{X(2 * ye + 80)}" rx="5" class="vitre"/>')
    s.append(f'<path d="{chemin_e(E_RE, X, Y)} Z" class="tube-fond"/><path d="{chemin_e(-E_RE, X, Y)} Z" class="plenum"/>')
    s.append(f'<path d="{chemin_e(E_RE, X, Y)}" class="tube-bord" fill="none"/><path d="{chemin_e(-E_RE, X, Y)}" class="tube-bord" fill="none"/>')
    for d in (-25, 0, 25):
        s.append(f'<path d="{chemin_e(d, X, Y)}" class="generatrice" fill="none"/>')
    s.append(f'<path d="{chemin_e(E_RF, X, Y)}" class="filtre" fill="none"/>')
    xpl = E_XR + E_RK - E_RE
    s.append(f'<path d="{chemin_e(-E_RE, X, Y)} Z" class="fente"/>')
    for xx in range(15, int(xpl), 15):
        s.append(f'<line x1="{X(xx)}" y1="{Y(E_YC - E_RE - 3)}" x2="{X(xx)}" y2="{Y(-E_YC + E_RE + 3)}" class="lame"/>')
    s.append(f'<circle cx="{X(xpl / 2)}" cy="0" r="{X(E_DV / 2)}" class="tangentiel"/>')
    s.append(f'<circle cx="{X(xpl / 2)}" cy="0" r="{X(16)}" class="tangentiel"/>')
    for yy in (-55, 55):
        s.append(f'<circle cx="{X(xpl / 2)}" cy="{Y(yy)}" r="7" class="sortant"/><circle cx="{X(xpl / 2)}" cy="{Y(yy)}" r="2.5" class="sortant-pt"/>')
    for a in range(-75, 76, 25):
        c, sn = math.cos(math.radians(a)), math.sin(math.radians(a))
        if abs(a) < 40:
            yk = max(-(E_YC - E_RK), min(E_YC - E_RK, 120 * sn))
            fleche((xo + 40, yk), (xo + 8, yk))
        else:
            cy = math.copysign(E_YC - E_RK, a)
            r1, r2 = E_RK + E_RE + 40, E_RK + E_RE + 8
            fleche((E_XR + r1 * c, cy + r1 * sn), (E_XR + r2 * c, cy + r2 * sn))
    for sg in (-1, 1):
        for xx in (20, 50):
            fleche((xx, sg * (ye + 40)), (xx, sg * (ye + 8)))
    # cotes et textes
    c = 'class="cote" marker-start="url(#fc)" marker-end="url(#fc)"'
    s.append(f'<line x1="{X(0)}" y1="{Y(-ye - 60)}" x2="{X(xo)}" y2="{Y(-ye - 60)}" {c}/>')
    t(xo / 2, -ye - 53, f"{f(xo)} mm dans la pièce", "middle")
    s.append(f'<line x1="{X(xo + 60)}" y1="{Y(ye)}" x2="{X(xo + 60)}" y2="{Y(-ye)}" {c}/>')
    t(xo + 66, 4, f"{f(2 * ye)} mm le long de la vitre")
    t(-16, ye + 45, "vitre", "end")
    t(xo + 66, ye - 10, f"tube Ø {f(2 * E_RE)} cintré, R {f(E_RK)} sur l'axe")
    t(xo + 66, ye - 22, "échangeur plissé + filtre")
    t(xo + 66, -ye + 32, f"bouche = tout le plénum, {f(xpl)} × {f(2 * (E_YC - E_RE))} mm")
    t(xo + 66, -ye + 20, "(air vers toi, lames du volet)")
    t(xo + 66, -ye + 8, f"ventilateur axial Ø {f(E_DV)} dessous (pointillé)")
    s.append(f'<line x1="{X(-6)}" y1="{Y(0)}" x2="{X(xo + 45)}" y2="{Y(0)}" class="trait-coupe"/>')
    t(xo + 45, -14, "A–A", "end")
    vb = f"{X(-60)} {Y(ye + 60)} {X(xo + 300)} {X(2 * ye + 140)}"
    return s, vb


def coupe_e():
    """Coupe A–A au milieu (y = 0), 1 mm = 2 px : vitre, pont, plénum + ventilateur + bouche, tube (fond du fer à cheval)."""
    k = 2.0
    X = lambda x: x * k
    Y = lambda z: -z * k
    P = lambda p: f"{X(p[0]):.1f},{Y(p[1]):.1f}"
    s = []
    t = lambda x, y, txt, a="start": s.append(f'<text x="{X(x):.1f}" y="{Y(y):.1f}" class="txt" text-anchor="{a}">{txt}</text>')

    def fleche(p1, p2, cls="air-froid", mk="fb"):
        s.append(f'<line x1="{X(p1[0]):.1f}" y1="{Y(p1[1]):.1f}" x2="{X(p2[0]):.1f}" y2="{Y(p2[1]):.1f}" class="{cls}" marker-end="url(#{mk})"/>')
    xt = E_XR + E_RK
    tp = lambda r, a: (xt + r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))
    xo, xpl = xt + E_RE, xt - E_RE
    zp, zh = E_Z_BAS, E_Z_HAUT
    # vitre, pont, bac
    s.append(f'<rect x="{X(-14)}" y="{Y(zh + 60)}" width="{X(11)}" height="{X(zh + 60 - (zp + 14))}" rx="5" class="vitre"/>')
    s.append(f'<path d="M{P((-80, zp + 10))} L{P((0, zp + 10))} L{P((0, zh))}" class="mur"/>')
    s.append(f'<path d="M{P((-80, zp - 10))} L{P((0, zp))} L{P((xo + 8, zp + 5))} L{P((xo + 8, zp + 15))}" class="mur"/>')
    s.append(f'<path d="M{P((2, zp + 1))} L{P((xo + 6, zp + 6))} L{P((xo + 6, zp + 8))} L{P((2, zp + 4))} Z" class="eau"/>')
    fleche((-10, zp - 4), (-75, zp - 10), "eau-f", "fe")
    # paroi du plénum côté tube : du bord haut de la sortie du tube jusqu'au dessus
    h0 = tp(E_RE, E_SORTIE_TUBE[0])
    s.append(f'<path d="M{P(h0)} Q{P((xpl, h0[1] + 8))} {P((xpl, h0[1] + 30))} L{P((xpl, zh))}" class="mur"/>')
    g0, g1 = tp(E_RE, E_SORTIE_TUBE[1]), tp(E_RE, E_SECT[0])
    s.append(f'<path d="M{P(g0)} A{X(E_RE)},{X(E_RE)} 0 0 0 {P(g1)}" class="mur"/>')
    # bouche (tout le plénum) et volet à lames
    s.append(f'<line x1="{X(0)}" y1="{Y(zh)}" x2="{X(xpl)}" y2="{Y(zh)}" class="bouche"/>')
    for xv in range(15, int(xpl), 15):
        s.append(f'<line x1="{X(xv)}" y1="{Y(zh - 16)}" x2="{X(xv)}" y2="{Y(zh)}" class="volet"/>')
        s.append(f'<line x1="{X(xv - 6)}" y1="{Y(zh - 15)}" x2="{X(xv + 6)}" y2="{Y(zh)}" class="volet-ch"/>')
    # ventilateur axial, axe vertical
    xc, zv, dv = xpl / 2, E_ZV, E_DV
    s.append(f'<rect x="{X(1)}" y="{Y(zv + 2)}" width="{X(xpl - 2)}" height="{X(4)}" class="ventilo"/>')
    s.append(f'<rect x="{X(xc - 14)}" y="{Y(zv + 14)}" width="{X(28)}" height="{X(22)}" rx="3" class="moyeu"/>')
    for sg in (-1, 1):
        s.append(f'<path d="M{P((xc + sg * 14, zv + 6))} L{P((xc + sg * dv / 2, zv + 2))} L{P((xc + sg * (dv / 2 - 2), zv + 11))} Z" class="pale"/>')
    # tube
    q0, q1 = tp(E_RE + 1.5, E_SECT[0]), tp(E_RE + 1.5, E_SECT[1])
    s.append(f'<path d="M{P(q0)} A{X(E_RE + 1.5)},{X(E_RE + 1.5)} 0 0 0 {P(q1)}" class="grille"/>')
    f0, f1 = tp(E_RF, E_SECT[0] + 3), tp(E_RF, E_SECT[1] - 3)
    s.append(f'<path d="M{P(f0)} A{X(E_RF)},{X(E_RF)} 0 0 0 {P(f1)}" class="filtre"/>')
    pts, _ = plis_arc(*E_SECT, E_RE, E_RI, E_PAS)
    s.append('<polyline points="' + " ".join(P((xt + u, z)) for u, z in pts) + '" class="pli" style="stroke-width:5"/>')
    for a in E_SECT:
        s.append(f'<line x1="{X(tp(E_RI, a)[0]):.1f}" y1="{Y(tp(E_RI, a)[1]):.1f}" x2="{X(tp(E_RE, a)[0]):.1f}" y2="{Y(tp(E_RE, a)[1]):.1f}" class="mur"/>')
    # air
    for a in range(-50, 131, 25):
        fleche(tp(E_RF + 22, a), tp(E_RF + 3, a))
    for zz in (-20, 0, 20):
        fleche((xt - E_RI + 4, zz), (xpl - 40, zz * 0.5 + 25), "air-froid fin")
    for xx in (35, 75, 115):
        fleche((xx, 5), (xx, zv - 6), "air-chaud", "fr")
        fleche((xx, zh + 5), (xx, zh + 32), "air-chaud", "fr")
    fleche((115, zh + 5), (140, zh + 28), "air-chaud pointe", "fr")
    fleche((35, zh + 5), (10, zh + 28), "air-chaud pointe", "fr")
    t(-8, zh + 65, "vitre", "middle")
    t(-78, zp + 14, "pont sous l'ouvrant")
    t(-78, zp - 22, "condensat vers l'extérieur")
    t(xt, zp - 12, "bac sous tout l'appareil", "middle")
    t(xpl + 8, zh + 4, f"bouche {f(xpl)} mm (tout le plénum), volet")
    t(xpl + 8, zv + 4, f"ventilateur axial Ø {f(dv)}")
    t(xo - 20, 75, f"tube Ø {f(2 * E_RE)} (fond du fer à cheval)")
    t(xpl / 2, -25, "plénum", "middle")
    c = 'class="cote" marker-start="url(#fc)" marker-end="url(#fc)"'
    s.append(f'<line x1="{X(xo + 35)}" y1="{Y(zh)}" x2="{X(xo + 35)}" y2="{Y(zp)}" {c}/>')
    t(xo + 39, (zh + zp) / 2, f"{f(zh - zp)} mm")
    s.append(f'<line x1="{X(0)}" y1="{Y(zp - 32)}" x2="{X(xo)}" y2="{Y(zp - 32)}" {c}/>')
    t(xo / 2, zp - 28, f"{f(xo)} mm", "middle")
    vb = f"{X(-85)} {Y(zh + 75)} {X(xo + 230)} {X(zh + 75 - zp + 50)}"
    return s, vb


def vue_face():
    """Vue de face, côté bouche de sortie (le long de l'axe), échelle 1 mm = 1 px."""
    k = 1.0
    s = []
    x0, x1 = 0, L
    yc = H_SORTIE + Y_INT - R_EXT          # haut du cylindre (même écart que sur la coupe)
    # cylindre (silhouette), plis vus comme génératrices
    s.append(f'<rect x="{x0}" y="{yc}" width="{L}" height="{2 * R_EXT}" class="cyl" rx="4"/>')
    for i in range(1, 12):
        y = yc + i * 2 * R_EXT / 12
        s.append(f'<line x1="{x0 + 4}" y1="{y}" x2="{x1 - 4}" y2="{y}" class="generatrice"/>')
    # bouche de sortie au-dessus
    s.append(f'<rect x="{x0}" y="0" width="{L}" height="{H_SORTIE}" class="bouche-face"/>')
    for i in range(6):
        cx = 37 + i * 75
        s.append(f'<circle cx="{cx}" cy="{H_SORTIE / 2}" r="12" class="sortant"/><circle cx="{cx}" cy="{H_SORTIE / 2}" r="3" class="sortant-pt"/>')
    # flasques et moteur
    s.append(f'<rect x="{-14}" y="{yc - 10}" width="14" height="{2 * R_EXT + 20}" class="flasque"/>'
             f'<rect x="{L}" y="{yc - 10}" width="14" height="{2 * R_EXT + 20}" class="flasque"/>')
    s.append(f'<rect x="{L + 14}" y="{yc + R_EXT - 30}" width="70" height="60" class="moteur" rx="6"/>'
             f'<text x="{L + 49}" y="{yc + R_EXT + 5}" class="txt" text-anchor="middle">moteur</text>')
    s.append(f'<text x="-20" y="{yc + R_EXT}" class="txt" text-anchor="end">collecteurs propane</text>')
    s.append(f'<text x="{L / 2}" y="{H_SORTIE + 22}" class="txt" text-anchor="middle">bouche de sortie {f(L)} × {f(H_SORTIE)} mm (air vers toi)</text>')
    s.append(f'<text x="{L / 2}" y="{yc + 2 * R_EXT + 26}" class="txt" text-anchor="middle">cylindre Ø {f(2 * R_EXT)} × {f(L)} mm, aspiration sur toute la longueur</text>')
    s.append(f'<line x1="0" y1="{yc + 2 * R_EXT + 40}" x2="{L}" y2="{yc + 2 * R_EXT + 40}" class="cote" marker-start="url(#fc)" marker-end="url(#fc)"/>')
    vb = f"-200 -20 {L + 320} {yc + 2 * R_EXT + 70}"
    return s, vb


def detail():
    """Détail de trois plis (échelle 1 mm = 6 px) : galette échangeuse pliée, tubes plats le long de l'axe."""
    k = 6.0
    s = []
    pas_ext = 2 * math.pi * R_EXT * PAS_PLI / 360        # largeur d'un pli à l'extérieur
    pas_int = 2 * math.pi * R_INT * PAS_PLI / 360
    prof = R_EXT - R_INT
    ep = 8.0                                           # épaisseur de la galette (profondeur traversée par l'air)
    # repère local : x tangentiel, y radial (0 = intérieur, prof = extérieur), redressé
    pts = []
    for i in range(7):
        x = i * pas_ext / 2
        y = prof - 3 if i % 2 == 0 else 3
        pts.append((x, y))
    X = lambda x: 20 + x * k
    Y = lambda y: 20 + (prof - y) * k
    s.append(f'<line x1="{X(-3)}" y1="{Y(prof)}" x2="{X(3 * pas_ext + 3)}" y2="{Y(prof)}" class="grille"/>')
    s.append(f'<line x1="{X(-3)}" y1="{Y(0)}" x2="{X(3 * pas_ext + 3)}" y2="{Y(0)}" class="pointille"/>')
    s.append('<polyline points="' + " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts) + f'" class="galette" style="stroke-width:{ep * k}"/>')
    s.append('<polyline points="' + " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in pts) + '" class="galette-axe"/>')
    # tubes plats (microcanaux) le long de l'axe, vus en coupe, au milieu de chaque flanc
    for i in range(6):
        (xa, ya), (xb, yb) = pts[i], pts[i + 1]
        ang = math.degrees(math.atan2(-(yb - ya), xb - xa))
        for t in (0.2, 0.43, 0.66, 0.89):
            xm, ym = xa + t * (xb - xa), ya + t * (yb - ya)
            s.append(f'<rect x="{X(xm) - (ep - 1) * k / 2}" y="{Y(ym) - 0.8 * k}" width="{(ep - 1) * k}" height="{1.6 * k}" rx="2" class="tube"'
                     f' transform="rotate({ang + 90:.1f} {X(xm):.1f} {Y(ym):.1f})"/>')
    # air : de l'extérieur (haut) vers l'intérieur (bas), à travers la galette
    for x in (pas_ext * 0.5, pas_ext * 1.5, pas_ext * 2.5):
        s.append(f'<line x1="{X(x)}" y1="{Y(prof + 6)}" x2="{X(x)}" y2="{Y(prof - 6)}" class="air-froid" marker-end="url(#fb)"/>')
    for x in (pas_ext * 1.0, pas_ext * 2.0):
        s.append(f'<line x1="{X(x)}" y1="{Y(8)}" x2="{X(x)}" y2="{Y(-6)}" class="air-froid" marker-end="url(#fb)"/>')
    s.append(f'<text x="{X(3 * pas_ext + 6)}" y="{Y(prof) + 4}" class="txt">extérieur (r = {f(R_EXT)})</text>')
    s.append(f'<text x="{X(3 * pas_ext + 6)}" y="{Y(0) + 4}" class="txt">chambre (r = {f(R_INT)})</text>')
    s.append(f'<text x="{X(3 * pas_ext + 6)}" y="{Y(prof / 2) + 4}" class="txt">pli de {f(prof)} mm</text>')
    s.append(f'<text x="{X(pas_ext * 0.5)}" y="{Y(prof + 9)}" class="txt" text-anchor="middle">pas ≈ {f(pas_ext, 0)} mm</text>')
    vb = f"0 -10 {X(3 * pas_ext) + 230} {Y(-10) + 20}"
    return s, vb, ep, pas_ext, pas_int


def contenu():
    """(css, corps HTML) des croquis, à insérer dans la page de l'échangeur (html_radial.py)."""
    s_c, vb_c, gorge, long_dev, sect = coupe("A")
    s_b, vb_b, *_ = coupe("B")
    s_a2, vb_a2, *_ = coupe("A2")
    s_k, vb_k, *_ = coupe("C")
    s_dd, vb_dd, ld_d, sect_d = coupe_d()
    s_e1, vb_e1 = vue_dessus_e()
    s_e2, vb_e2 = coupe_e()
    a_gal_e, a_fil_e, a_sor_e, lg_e, a_bou_e = surfaces_e()
    l_e = ""
    a_fente_e = a_bou_e
    for nom, q in (("pièce (clim)", 570), ("pièce (chauffage)", 830)):
        Q = q / 3600
        v = Q / a_fente_e
        l_e += (f"<tr><td>{nom}</td><td class=n>{f(q)}</td><td class=n>{f(Q / a_fil_e, 2)}</td><td class=n>{f(Q / a_gal_e, 2)}</td>"
                f"<td class=n>{f(Q / a_sor_e, 1)}</td><td class=n>{f(v, 1)}</td><td class=n>{f(0.6 * v * v, 0)}</td></tr>")
    A_env_d = 2 * math.pi * R_EXT * sect_d / 360 * L * 1e-6
    A_pli_d = ld_d * L * 1e-6
    A_fil_d = 2 * math.pi * R_FILTRE * (sect_d - 8) / 360 * L * 1e-6
    A_col, A_sor = D_COL * L * 1e-6, D_LARG * L * 1e-6
    ld_dd = ""
    for nom, q in (("extérieur (clim)", 2500), ("pièce (chauffage)", 830), ("pièce (clim)", 570)):
        Q = q / 3600
        ld_dd += (f"<tr><td>{nom}</td><td class=n>{f(q)}</td><td class=n>{f(Q / A_fil_d, 1)}</td><td class=n>{f(Q / A_pli_d, 1)}</td>"
                  f"<td class=n>{f(Q / A_col, 1)}</td><td class=n>{f(Q / A_sor, 1)}</td><td class=n>{f(0.6 * (Q / A_sor) ** 2, 0)}</td></tr>")
    q0 = 2500 / 3600
    v_g = q0 / (gorge * L * 1e-6)
    pd_g = 0.6 * v_g ** 2
    s_f, vb_f = vue_face()
    s_d, vb_d, ep, pas_ext, pas_int = detail()
    arc_ext = 2 * math.pi * R_EXT * sect / 360
    A_env = arc_ext * L * 1e-6
    A_pli = long_dev * L * 1e-6
    A_ch = 2 * math.pi * R_INT * sect / 360 * L * 1e-6
    A_gorge = gorge * L * 1e-6
    A_bouche = H_SORTIE * L * 1e-6
    A_fA = 2 * math.pi * R_FILTRE * sect / 360 * L * 1e-6
    A_fB = H_SORTIE * L * 1e-6 * PLI_FILTRE
    lf = ""
    for nom, q in (("extérieur (clim)", 2500), ("pièce (chauffage)", 830), ("pièce (clim)", 570)):
        Q = q / 3600
        lf += (f"<tr><td>{nom}</td><td class=n>{f(q)}</td><td class=n>{f(Q / A_fA, 1)}</td>"
               f"<td class=n>{f(Q / (H_SORTIE * L * 1e-6), 1)}</td><td class=n>{f(Q / A_fB, 1)}</td></tr>")
    lignes = ""
    for q in DEBITS:
        Q = q / 3600
        lignes += (f"<tr><td class=n>{f(q)}</td><td class=n>{f(Q / A_env, 1)}</td><td class=n>{f(Q / A_pli, 1)}</td>"
                   f"<td class=n>{f(Q / A_ch, 1)}</td><td class=n>{f(Q / A_gorge, 1)}</td><td class=n>{f(Q / A_bouche, 1)}</td>"
                   f"<td class=n>{f(0.6 * (Q / A_bouche) ** 2, 0)}</td></tr>")
    defs = """<defs>
<marker id="fb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#1c7ed6"/></marker>
<marker id="fr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#e03131"/></marker>
<marker id="fn" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#495057"/></marker>
<marker id="fe" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#1098ad"/></marker>
<marker id="fc" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#868e96"/></marker>
</defs>"""
    css = """
:root{--fond:#f8f9fa;--carte:#fff;--texte:#212529;--doux:#5c636a;--trait:#dee2e6}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--fond:#141517;--carte:#1f2023;--texte:#e9ecef;--doux:#adb5bd;--trait:#373a40}}
:root[data-theme=dark]{--fond:#141517;--carte:#1f2023;--texte:#e9ecef;--doux:#adb5bd;--trait:#373a40}
body{margin:0;background:var(--fond);color:var(--texte);font:15px/1.5 system-ui,sans-serif} main{max-width:1100px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:24px;margin:0 0 6px} h2{font-size:18px;margin:26px 0 8px} .aide{color:var(--doux);font-size:13px}
.carte{background:var(--carte);border:1px solid var(--trait);border-radius:10px;padding:12px 16px;overflow-x:auto}
.dessin{background:#fff;border:1px solid var(--trait);border-radius:10px;padding:8px} svg{width:100%;height:auto;display:block}
.grille2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
table{border-collapse:collapse;width:100%;font-size:14px} td,th{padding:5px 8px;border-bottom:1px solid var(--trait);text-align:left} td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
svg .mur{fill:none;stroke:#343a40;stroke-width:3} svg .bouche{stroke:#e03131;stroke-width:2;stroke-dasharray:6 4}
svg .grille{fill:none;stroke:#adb5bd;stroke-width:1.5;stroke-dasharray:3 3} svg .pointille{stroke:#adb5bd;stroke-width:1;stroke-dasharray:4 4}
svg .pli{fill:none;stroke:#2f9e44;stroke-width:4;stroke-linejoin:round} svg .rotor{fill:#f1f3f5;stroke:#495057;stroke-width:1.5}
svg .aube{fill:none;stroke:#495057;stroke-width:2} svg .axe{fill:#495057} svg .rotation{fill:none;stroke:#495057;stroke-width:2}
svg .air-froid{stroke:#1c7ed6;stroke-width:2.5;fill:none} svg .air-froid.fin{stroke-width:1.5;stroke-dasharray:4 3}
svg .air-chaud{stroke:#e03131;stroke-width:3;fill:none} svg .cote{stroke:#868e96;stroke-width:1}
svg .txt{font:13px system-ui,sans-serif;fill:#343a40} svg .cyl{fill:#ebfbee;stroke:#2f9e44;stroke-width:2}
svg .generatrice{stroke:#2f9e44;stroke-width:1;opacity:.6} svg .bouche-face{fill:#fff5f5;stroke:#e03131;stroke-width:2}
svg .sortant{fill:none;stroke:#e03131;stroke-width:2} svg .sortant-pt{fill:#e03131} svg .flasque{fill:#ced4da;stroke:#495057}
svg .moteur{fill:#dee2e6;stroke:#495057} svg .galette{fill:none;stroke:#b2f2bb;stroke-linejoin:round} svg .galette-axe{fill:none;stroke:#2f9e44;stroke-width:1.5;stroke-dasharray:5 4}
svg .tube{fill:#ffc9c9;stroke:#c92a2a;stroke-width:1.5}
svg .ventilo{fill:#f8f9fa;stroke:#495057;stroke-width:2} svg .moyeu{fill:#495057} svg .pale{fill:#adb5bd;stroke:#495057}
svg .repartiteur{fill:none;stroke:#868e96;stroke-width:2;stroke-dasharray:2 5}
svg .filtre{fill:none;stroke:#f08c00;stroke-width:3;stroke-dasharray:2 3}
svg .vitre{fill:#a5d8ff;stroke:#343a40;stroke-width:1.5} svg .eau{fill:#99e9f2;stroke:#1098ad} svg .eau-f{stroke:#1098ad;stroke-width:2}
svg .volet{stroke:#343a40;stroke-width:4;stroke-linecap:round} svg .volet-ch{stroke:#343a40;stroke-width:2;stroke-dasharray:4 3;stroke-linecap:round}
svg .plenum{fill:#f8f9fa;stroke:none} svg .tube-fond{fill:#ebfbee;stroke:none} svg .tube-bord{fill:none;stroke:#2f9e44;stroke-width:2.5}
svg .fente{fill:#fff5f5;stroke:#e03131;stroke-width:2} svg .tangentiel{fill:none;stroke:#495057;stroke-width:1.5;stroke-dasharray:5 4}
svg .trait-coupe{stroke:#868e96;stroke-width:1;stroke-dasharray:12 4 2 4}
svg .lame{stroke:#e03131;stroke-width:1;opacity:.5}
svg .air-chaud.pointe{stroke-dasharray:6 4;stroke-width:2}"""
    corps = f"""<p class=aide>Croquis à l'échelle pour vérifier l'idée, pas un dessin de fabrication. Cylindre couché Ø {f(2 * R_EXT)} × {f(L)} mm.
Bleu : air aspiré. Rouge : air rejeté. Vert : échangeur plissé.</p>

<h2 id=variante-e>Variante E (proposée) : tube cintré en fer à cheval, bouche sur tout le plénum</h2>
<p class=aide>D'après ton dessin vu de dessus, avec tes cotes : <b>{f(E_LARG)} mm le long de la vitre, {f(E_PROF)} mm dans la pièce,
{f(E_HAUT)} mm de haut, tube Ø {f(2 * E_RE)}</b>. Le tube (échangeur plissé + filtre, bas fermé) est cintré en fer à cheval, rayon
{f(E_RK)} mm sur l'axe ; ses deux branches s'appuient sur la vitre. L'air de la pièce entre par l'extérieur du fer à cheval,
traverse l'échangeur, ressort par la face intérieure du tube dans le plénum central. Un ventilateur axial à axe vertical
(Ø {f(E_DV)}) le souffle vers le haut, par une bouche qui occupe <b>tout le plénum</b> ({f(E_XR + E_RK - E_RE)} × {f(2 * (E_YC - E_RE))} mm,
coins arrondis), avec un volet à lames.</p>
<h3>Vue de dessus</h3>
<div class=dessin style="max-width:820px"><svg viewBox="{vb_e1}">{defs}{''.join(s_e1)}</svg></div>
<h3>Vue de côté : coupe A–A au milieu</h3>
<div class=dessin style="max-width:820px"><svg viewBox="{vb_e2}">{defs}{''.join(s_e2)}</svg></div>
<p class=aide>Coupe du tube : plis de {f(E_RE - E_RI)} mm tous les {f(E_PAS)}° (la galette de 8 mm doit tenir au fond du pli, à r = {f(E_RI)} mm) ;
ouverture vers le plénum sur {f(E_SORTIE_TUBE[1] - E_SORTIE_TUBE[0])}°, échangeur sur {f(E_SECT[1] - E_SECT[0])}°, reste du dessous fermé (gouttière).
Un bac unique sous l'appareil, en pente vers la vitre, renvoie le condensat dehors par le pont.</p>
<div class=carte><table>
<tr><th>Cas</th><th class=n>Débit (m³/h)</th><th class=n>filtre<br>{f(a_fil_e, 3)} m²</th><th class=n>galette plissée<br>{f(a_gal_e, 3)} m²</th>
<th class=n>sortie du tube<br>vers le plénum {f(a_sor_e, 3)} m²</th><th class=n>bouche<br>{f(a_bou_e, 3)} m²</th><th class=n>énergie perdue<br>à la sortie (Pa)</th></tr>{l_e}</table>
<p class=aide>Vitesses en m/s. Tube de {f(lg_e)} mm sur son axe. <b>Les vitesses de passage sont maintenant correctes</b> : la bouche
souffle à 5 à 8 m/s, comme un split. Dans le ventilateur Ø {f(E_DV)}, l'air passe à {f(570 / 3600 / (math.pi * (E_DV / 2000) ** 2), 0)} à
{f(830 / 3600 / (math.pi * (E_DV / 2000) ** 2), 0)} m/s : c'est un ventilateur rapide et bruyant (type serveur).<br>
<b>Le point faible est la surface d'échange</b> : {f(a_gal_e, 3)} m² de galette, soit {f(100 * a_gal_e / A_pli_d)} % de la variante D et
{f(100 * a_gal_e / A_pli)} % de A′. Ordre de grandeur : une galette de 8 mm à ailettes persiennes (≈ 12 m² d'ailettes par m² frontal,
h ≈ 80 W/m²K à 1,8 m/s) donne hA ≈ {f(round(a_gal_e * 12 * 80 * 0.85, -1))} W/K, alors qu'il en faut ≈ 570 à 620 côté pièce en chauffage
(critères du module) : il manque un facteur 5 environ. Avec un tube Ø 100, on ne peut gagner ni en profondeur de pli ni en épaisseur de galette.</p></div>
<div class=carte style="margin-top:10px"><table>
<tr><th>Pour</th><th>Contre / à régler</th></tr>
<tr><td>Très compact : {f(E_LARG)} × {f(E_PROF)} × {f(E_HAUT)} mm</td>
<td><b>hA</b> ≈ 5 fois trop faible avec un tube Ø 100 (surface de galette {f(a_gal_e, 3)} m²)</td></tr>
<tr><td>Bouche large (tout le plénum) : 5 à 8 m/s, peu de perte de sortie</td>
<td>Ventilateur Ø {f(E_DV)} à 10–15 m/s : bruit ; un seul gros axial ne tient pas dans le plénum</td></tr>
<tr><td>Fente au centre, tube tout autour : chemins presque égaux, débit bien réparti</td>
<td>Bouche entourée d'aspirations : réaspiration possible (surtout en chauffage), lèvres à prévoir</td></tr>
<tr><td>Bac unique, pente vers la vitre ; réfrigérant et condensat passent par les branches et le pont</td>
<td>Plis cintrés : écartés à l'extérieur du cintre, serrés à l'intérieur</td></tr>
</table></div>

__VUE3D_E__

<h2 id=variante-d>Variante D (proposée) : soufflage par le haut, ventilateur dans la cheminée, bac à condensats</h2>
<div class=dessin><svg viewBox="{vb_dd}">{defs}{''.join(s_dd)}</svg></div>
<p class=aide>D'après ton dessin : l'appareil est « en selle », relié à la partie extérieure par un pont qui passe sous l'ouvrant baissé.
L'air de la pièce est aspiré à travers le filtre et l'échangeur sur deux secteurs ({f(D_ARCS[0][1] - D_ARCS[0][0])}° à droite,
{f(D_ARCS[1][1] - D_ARCS[1][0])}° à gauche), se rassemble dans la chambre vide et monte dans la cheminée. Le ventilateur axial,
à axe vertical, est dans le col de la cheminée ({f(D_COL)} mm) ; un convergent mène à la fente de sortie de {f(D_LARG)} × {f(L)} mm, qui souffle
vers le haut, le long de la vitre. Le bas du cylindre est fermé sur 60° :
il sert de gouttière, et l'eau des plis tombe dans le bac, qui se vide par gravité vers l'extérieur par le pont. Un volet à lames règle la
sortie : verticale en clim (l'air froid monte au plafond), inclinée vers la pièce en chauffage.</p>
<div class=carte><table>
<tr><th>Module</th><th class=n>Débit (m³/h)</th><th class=n>filtre<br>{f(A_fil_d, 3)} m²</th><th class=n>galette plissée<br>{f(A_pli_d, 3)} m²</th>
<th class=n>col de cheminée<br>{f(D_COL)} × {f(L)}</th><th class=n>fente de sortie<br>{f(D_LARG)} × {f(L)}</th><th class=n>énergie perdue<br>à la sortie (Pa)</th></tr>{ld_dd}</table>
<p class=aide>Vitesses en m/s. Échangeur sur {f(sect_d)}° au lieu de 280° pour A′ (à longueur égale) : {f(A_pli_d, 3)} m² de galette contre {f(A_pli, 3)} m²
(−{f(100 * (1 - A_pli_d / A_pli))} %). La fente de {f(D_LARG)} mm donne un jet rapide, comme un split mural (≈ 6 à 8 m/s) : bonne portée,
mais l'énergie du jet est perdue (dernière colonne) et s'ajoute à ce que le ventilateur doit fournir. Côté extérieur, 2 500 m³/h par
cette fente n'est pas réaliste ({f(2500 / 3600 / (D_LARG * L * 1e-6), 0)} m/s) : le module extérieur aura une sortie plus grande.</p></div>
<div class=carte style="margin-top:10px"><table>
<tr><th>Pour</th><th>Contre / à régler</th></tr>
<tr><td>Plus de volute : moins de volume, moins de pièces, moins de pertes</td>
<td><b>Surface d'échange</b> réduite d'environ 22 % par rapport à A′ (cheminée en haut, bac en bas)</td></tr>
<tr><td>Soufflage vertical : bon en clim (plafond), correct en chauffage (coupe la descente d'air froid de la vitre)</td>
<td>En chauffage l'air chaud monte : le volet doit pouvoir l'incliner vers la pièce ; la vitre est un peu plus chaude (pertes)</td></tr>
<tr><td>Fente étroite et rapide : jet qui porte loin, comme un split ; peu de place prise au-dessus du cylindre</td>
<td>À 830 m³/h (chauffage) : {f(830 / 3600 / (D_LARG * L * 1e-6), 1)} m/s et ≈ {f(0.6 * (830 / 3600 / (D_LARG * L * 1e-6)) ** 2, 0)} Pa perdus, bruit de jet ;
le ventilateur doit fournir 60 à 110 Pa au total</td></tr>
<tr><td>Condensat : point bas unique, vidange par le pont sans pompe</td>
<td>Les plis doivent guider l'eau jusqu'aux bords du bac sans qu'elle soit reprise par l'air (vitesse frontale faible ici : &lt; 1 m/s)</td></tr>
<tr><td>Sortie opposée au pont et éloignée de l'aspiration basse ; aspiration presque symétrique</td>
<td>Les plis du haut, près de la cheminée, aspireront plus que ceux du bas (chemin court) : à vérifier en CFD 2D</td></tr>
<tr><td>Ventilateur dans la cheminée : air filtré, accessible par le haut</td>
<td><b>Type de ventilateur</b> : avec 60 à 110 Pa à fournir, des axiaux Ø 140 dans le col sont à la limite. Un ventilateur tangentiel
Ø 80 à 100 × {f(L)} mm logé dans le col, ou un petit centrifuge, convient mieux à une fente de {f(D_LARG)} mm (c'est la solution des splits)</td></tr>
</table></div>

<h2>Variante A′ : coupe transversale</h2>
<div class=dessin><svg viewBox="{vb_a2}">{defs}{''.join(s_a2)}</svg></div>
<p class=aide>Même sens d'air que la variante A (plus bas) : l'air est aspiré à travers le manchon filtrant et l'échangeur plissé sur {f(sect)}°, se rassemble
dans la chambre vide, passe la gorge et la volute, puis un ventilateur du commerce placé juste avant la bouche le rejette vers la droite.
Le ventilateur aspire : l'échangeur est en dépression (siphon pour le condensat) et le ventilateur voit de l'air déjà filtré.</p>
<div class=carte><table>
<tr><th></th><th>A′ : ventilateur simple qui aspire (tirer)</th><th>C : ventilateur simple qui souffle (pousser)</th></tr>
<tr><td>Répartition dans l'échangeur</td><td>meilleure : la chambre est un « puits » vers la gorge ; les plis proches de la gorge tirent
un peu plus, sans jet. À vérifier en CFD</td><td>jet de ≈ {f(v_g, 0)} m/s dans la chambre : sort surtout en face de la gorge ; répartiteur perforé conseillé</td></tr>
<tr><td>Filtre</td><td>manchon autour du cylindre, ≈ 1 m/s côté pièce</td><td>plissé dans la bouche, ≈ 1 m/s côté pièce une fois plissé ×3</td></tr>
<tr><td>Ventilateur</td><td>dans la volute, avant la bouche ; mêmes contraintes de taille que C (bouche {f(H_SORTIE)} × {f(L)} mm)</td><td>idem</td></tr>
<tr><td>Recirculation côté extérieur</td><td>sortie au-dessus de l'aspiration droite : déflecteur à prévoir</td><td>favorable (aspiration en bas, sortie en haut), sauf le bas de l'échangeur</td></tr>
<tr><td>Côté pièce</td><td>un seul jet orientable</td><td>sortie de tous les côtés</td></tr>
</table></div>

<h2>Variante A : ventilateur tangentiel dans le cylindre (première idée)</h2>
<div class=dessin><svg viewBox="{vb_c}">{defs}{''.join(s_c)}</svg></div>
<p class=aide>Le ventilateur tangentiel (rotor Ø {f(2 * R_ROT)}, tourne dans le sens horaire) aspire l'air à travers la paroi plissée
sur {f(sect)}°, y compris par le dessus, entre la volute et le cylindre. Il le rejette par le secteur libre de gauche
({f(SECT[0])}° à {f(SECT[1])}°), entre le bec et la paroi arrière. La volute remonte et sort vers la droite, au-dessus du cylindre,
comme sur ton dessin. Elle est dessinée à la taille qu'il lui faut pour 2 500 m³/h (voir le tableau).</p>

<h2>Variante B : cylindre en haut, aspiration en bas, sens de l'air inversé</h2>
<div class=dessin><svg viewBox="{vb_b}">{defs}{''.join(s_b)}</svg></div>
<p class=aide>Même coupe retournée. L'air frais est aspiré en bas par la volute, le ventilateur le pousse dans la chambre, et il
ressort à travers l'échangeur plissé sur {f(sect)}°, vers le haut et les côtés. Les vitesses sont les mêmes que pour la variante A
(tableau en bas de page) ; seul le sens change. Attention : le bas de l'échangeur souffle vers le bas, entre le cylindre et la volute,
juste au-dessus de la bouche d'aspiration. Pour éviter que cet air soit réaspiré, on peut fermer le bas de l'échangeur (≈ 60°, ce qui
réduit la surface d'environ 20 %) ou le prolonger d'un déflecteur.</p>
<div class=carte><table>
<tr><th></th><th>A : aspiration par l'échangeur (tirer)</th><th>B : soufflage par l'échangeur (pousser)</th></tr>
<tr><td>Répartition de l'air dans l'échangeur</td><td>bonne : l'aspiration répartit l'air d'elle-même</td>
<td><b>mauvaise</b> sans précaution : un tangentiel souffle un jet étroit (≈ 90 à 120° de sortie) ; il faut une chambre de détente
ou des déflecteurs pour l'étaler sur {f(sect)}°</td></tr>
<tr><td>Ventilateur</td><td>tangentiel classique (entrée large, sortie étroite)</td>
<td>tangentiel à contre-emploi (sortie très large) ; une roue centrifuge serait plus logique mais elle aspire par les bouts, pas par une volute latérale</td></tr>
<tr><td>Recirculation côté extérieur</td><td>sortie juste au-dessus de l'aspiration droite : risque, déflecteur à prévoir</td>
<td><b>favorable</b> : l'air frais est pris en bas, l'air chaud part en haut et monte tout seul (sauf le bas de l'échangeur, à fermer ou dévier)</td></tr>
<tr><td>Côté pièce</td><td>un seul jet orientable vers la pièce</td><td>l'air sort de tous les côtés, y compris vers la fenêtre</td></tr>
<tr><td>Condensat (évaporateur)</td><td>échangeur en dépression : siphon nécessaire</td><td>échangeur en surpression : l'eau s'écoule sans siphon,
mais les gouttes peuvent être soufflées hors des plis</td></tr>
<tr><td>Poussière, givre</td><td>l'échangeur filtre l'air avant le ventilateur</td><td>le ventilateur voit l'air brut ; un filtre en entrée de volute est facile à loger</td></tr>
</table></div>

<h2>Variante C : ventilateur simple juste après le filtre, chambre vide</h2>
<div class=dessin><svg viewBox="{vb_k}">{defs}{''.join(s_k)}</svg></div>
<p class=aide>Comme la variante B, mais le ventilateur est un ventilateur courant (axial ou centrifuge du commerce) placé dans la volute,
juste après le filtre. Il pousse l'air dans le cylindre, qui n'est plus qu'une chambre vide ; l'air ressort à travers l'échangeur plissé.</p>
<div class=carte><table>
<tr><th>Pour</th><th>Contre</th></tr>
<tr><td>Ventilateur du commerce, simple, meilleur rendement qu'un tangentiel (40 à 60 % contre 30 à 40 %)</td>
<td><b>Répartition</b> : l'air entre dans la chambre en jet par la gorge ({f(gorge)} × {f(L)} mm, {f(v_g, 0)} m/s à 2 500 m³/h,
pression dynamique ≈ {f(pd_g, 0)} Pa). L'échangeur ne freine que de 10 à 25 Pa : le jet traverse la chambre et sort surtout par
le côté opposé à la gorge. Il faut un répartiteur perforé (tube percé dans la chambre) ou des aubes, qui coûtent de la perte de charge.</td></tr>
<tr><td>Le ventilateur voit de l'air filtré et propre ; le filtre est juste devant, facile d'accès</td>
<td><b>Forme du ventilateur</b> : la bouche fait {f(H_SORTIE)} × {f(L)} mm. Un ventilateur rond de cette hauteur (Ø 170) ne passe
qu'environ 600 à 900 m³/h sous 50 Pa : il en faudrait 2 ou 3 côte à côte pour 2 500 m³/h, ou une volute plus haute pour un seul Ø 250 à 300.</td></tr>
<tr><td>Cylindre vide : fabrication simple, rien qui tourne près des plis</td>
<td>Pas d'aspiration sur 280° : la sortie se fait partout, avec les remarques de la variante B (bas de l'échangeur, côté pièce)</td></tr>
<tr><td>CFD simple : le ventilateur se modélise par un saut de pression (sa courbe), calcul stationnaire</td><td></td></tr>
</table></div>

<h2>Où mettre le filtre</h2>
<div class=carte><table>
<tr><th>Module</th><th class=n>Débit (m³/h)</th><th class=n>A : manchon autour du cylindre<br>{f(A_fA, 3)} m²</th>
<th class=n>B : filtre plat dans la bouche<br>{f(H_SORTIE * L * 1e-6, 3)} m²</th><th class=n>B : filtre plissé ×{f(PLI_FILTRE)}<br>{f(A_fB, 3)} m²</th></tr>{lf}</table>
<p class=aide>Vitesse de l'air dans le filtre, en m/s. La perte de charge d'un média filtrant croît à peu près comme la vitesse ;
un filtre se dimensionne normalement pour 1 à 2,5 m/s. <b>A</b> : un manchon (chaussette) en média lavable enfilé sur le cylindre
par un bout ; grande surface, donc vitesse basse, et il se retire en le faisant glisser. <b>B</b> : tout l'air passe par la bouche,
{f(H_SORTIE)} × {f(L)} mm ; un filtre plat y verrait 9 m/s, il faut le plisser et l'élargir. Côté extérieur, les climatiseurs n'ont en
général qu'une grille contre les feuilles et les insectes : le vrai filtre est côté pièce, où le débit est 3 à 4 fois plus faible.</p></div>

<h2>Vue de face, côté bouche (variante A)</h2>
<div class=dessin><svg viewBox="{vb_f}">{defs}{''.join(s_f)}</svg></div>
<p class=aide>Tout travaille sur la longueur : la paroi plissée aspire sur 450 mm et la bouche souffle sur 450 mm. Le moteur est à un bout,
sur l'axe du rotor. Les tubes de propane courent le long de l'axe, dans les plis, et se raccordent à des collecteurs logés dans les flasques.</p>

<h2>Détail de trois plis (redressés)</h2>
<div class=dessin><svg viewBox="{vb_d}">{defs}{''.join(s_d)}</svg></div>
<p class=aide>La paroi est une galette d'échangeur d'environ {f(ep)} mm d'épaisseur, pliée en accordéon sur {f(R_EXT - R_INT)} mm de profondeur.
Les rectangles rouges sont les tubes plats de propane (microcanaux), vus en coupe : ils courent le long de l'axe, leur grand côté
dans le sens de l'air. L'air entre dans les plis ouverts vers l'extérieur, traverse la galette ({f(ep)} mm) entre les tubes et
ressort dans les plis ouverts vers la chambre. Les ailettes entre les tubes ne sont pas dessinées.</p>

<h2>Vitesses de l'air (Ø {f(2 * R_EXT)} × {f(L)}, aspiration sur {f(sect)}°)</h2>
<div class=carte><table>
<tr><th class=n>Débit (m³/h)</th><th class=n>sur l'enveloppe<br>{f(A_env, 3)} m²</th><th class=n>dans la galette plissée<br>{f(A_pli, 3)} m² (×{f(A_pli / A_env, 1)})</th>
<th class=n>entrée de la chambre<br>{f(A_ch, 3)} m²</th><th class=n>gorge de sortie<br>{f(gorge)} × {f(L)}</th><th class=n>bouche<br>{f(H_SORTIE)} × {f(L)}</th>
<th class=n>énergie perdue à la bouche (Pa)</th></tr>{lignes}</table>
<p class=aide>Vitesses en m/s. La dernière colonne est la pression dynamique ρu²/2 de l'air qui quitte la bouche, perdue sauf si la volute
s'élargit encore (diffuseur).</p></div>"""
    return css, corps


def main():
    """Page autonome des croquis (la page principale est echangeur_radial.html, qui les inclut)."""
    css, corps = contenu()
    corps = corps.replace("__VUE3D_E__", "")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(f"""<!doctype html><html lang=fr><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Échangeur radial, croquis</title><style>{css}</style></head><body><main>
<h1>Échangeur cylindrique à flux radial : croquis 2D</h1>{corps}</main></body></html>""")
    print(SORTIE)


if __name__ == "__main__":
    main()
