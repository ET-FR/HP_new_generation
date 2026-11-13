"""Profils le long du chemin d'air de l'échangeur Ø 150 : température de mélange et pression, de l'entrée à la sortie.

Tourne sur la machine de calcul, dans le dossier du cas reconstruit, sur le maillage complet (valeurs par maille).
Chemin découpé en trois parties, abscisse s (mm) mesurée sur le chemin moyen :
  conduit d'entrée   boîte x ∈ [Rc, Ri], y ∈ [−Ld, 0], z ∈ [0, gap] ; s = y + Ld ; débit selon +y
  hélice             angle déroulé θ ∈ [0, θ_fin] : maille (φ, z) → θ = φ + 2π·floor((z − pas·φ/2π)/pas) ;
                     s = Ld + θ·√(r_m² + (pas/2π)²), r_m = (Rc + Ri)/2 ; débit = vitesse tangentielle
  conduit de sortie  boîte tournée de θ_fin, z ≥ Lint − gap ; s = Ld + L_hélice + y' ; débit selon la tangente
Coupes exactes du maillage (plans tous les 5 mm dans les conduits, demi-plans méridiens tous les 3° dans l'hélice,
découpés en tours par z) ; sur chaque section :
  T de mélange  = Σ T·u_n·dA / Σ u_n·dA     p moyenne = Σ p·dA / Σ dA
  débit         = Σ u_n·dA (contrôle : doit valoir le débit d'entrée partout)
Sortie : profils.json.

    python3 profils_chemin_d150.py <cas> <dimensions.json>
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pyvista as pv

cas = Path(sys.argv[1]).resolve()
dim = json.loads(Path(sys.argv[2]).read_text())
p = dim["parametres"]
Ri = dim["rayons_mm"]["interieur"] * 1e-3
Rc = dim["rayons_mm"]["noyau"] * 1e-3
pas = dim["helice"]["pas_mm"] * 1e-3
gap = pas - p["ep_ailette"] * 1e-3
Lint = dim["longueur_interieure_mm"] * 1e-3
Ld = p["conduit_long"] * 1e-3
th_fin = dim["helice"]["tours"] * 2 * math.pi
rm = (Rc + Ri) / 2
ds_dth = math.hypot(rm, pas / (2 * math.pi))
L_hel = th_fin * ds_dth

(cas / "cas.foam").touch()
r = pv.OpenFOAMReader(str(cas / "cas.foam"))
r.set_active_time_value(max(r.time_values))
r.disable_all_patch_arrays()
r.enable_patch_array("internalMesh")
r.cell_to_point_creation = False
m = r.read()["internalMesh"]
U = m.cell_data["U"]
P = m.cell_data["p"] * 1.204
print("mailles", m.n_cells, flush=True)
m.cell_data["pPa"] = P


def coupe(origine, normale, garder):
    """Coupe exacte du maillage par un plan ; garder(centres) choisit la partie utile. Renvoie aire, débit, T et p moyens."""
    sl = m.slice(normal=normale, origin=origine, generate_triangles=False)
    if sl.n_cells == 0:
        return None
    sl = sl.compute_cell_sizes(length=False, area=True, volume=False)
    cc = sl.cell_centers().points
    q = garder(cc)
    if q.sum() < 3:
        return None
    a = np.abs(sl.cell_data["Area"][q])
    un = sl.cell_data["U"][q] @ np.asarray(normale)
    w = un * a
    return dict(aire_mm2=float(a.sum() * 1e6), debit_m3h=float(w.sum() * 3600),
                Tf=float((sl.cell_data["Tf"][q] * w).sum() / w.sum()), Tp=float((sl.cell_data["Tp"][q] * w).sum() / w.sum()),
                p_Pa=float((sl.cell_data["pPa"][q] * a).sum() / a.sum()))


res = []
tol = 1e-4
# conduit d'entrée : plans y = cte, flux selon +y ; on garde x ∈ [Rc, Ri], z ≤ gap, hors canal de l'hélice
for sm in np.arange(2.5e-3, Ld, 5e-3):
    yy = -Ld + sm
    r_ = coupe((0, yy, 0), (0, 1, 0), lambda c: (c[:, 0] > Rc - tol) & (c[:, 0] < Ri + tol) & (c[:, 2] < gap + tol))
    if r_:
        res.append(dict(partie="entree", s_mm=round(sm * 1e3, 2), **r_))
# hélice : demi-plans méridiens tous les 3°, découpés en tours par z
for ph in np.radians(np.arange(0, 360, 3)):
    n = (-math.sin(ph), math.cos(ph), 0.0)
    for k in range(0, 4):
        th = ph + 2 * math.pi * k
        if th > th_fin:
            continue
        z0 = pas * th / (2 * math.pi)
        r_ = coupe((0, 0, 0), n, lambda c, z0=z0, ph=ph: (c[:, 0] * math.cos(ph) + c[:, 1] * math.sin(ph) > 0)
                   & (np.hypot(c[:, 0], c[:, 1]) < Ri + tol) & (c[:, 2] > z0 - tol) & (c[:, 2] < z0 + gap + tol))
        if r_:
            res.append(dict(partie="helice", s_mm=round((Ld + th * ds_dth) * 1e3, 2), tour=round(th / (2 * math.pi), 3), **r_))
# conduit de sortie : plans perpendiculaires à la tangente de sortie
ct, st = math.cos(th_fin), math.sin(th_fin)
t = (-st, ct, 0.0)
for sm in np.arange(2.5e-3, Ld, 5e-3):
    org = (sm * t[0], sm * t[1], 0)
    r_ = coupe(org, t, lambda c: ((c[:, 0] * ct + c[:, 1] * st) > Rc - tol) & ((c[:, 0] * ct + c[:, 1] * st) < Ri + tol)
               & (c[:, 2] > Lint - gap - tol))
    if r_:
        res.append(dict(partie="sortie", s_mm=round((Ld + L_hel + sm) * 1e3, 2), **r_))
res.sort(key=lambda d: d["s_mm"])
meta = dict(L_entree_mm=Ld * 1e3, L_helice_mm=L_hel * 1e3, L_sortie_mm=Ld * 1e3, pas_mm=pas * 1e3,
            tours=dim["helice"]["tours"], ds_par_tour_mm=2 * math.pi * ds_dth * 1e3, r_moyen_mm=rm * 1e3)
(cas / "profils.json").write_text(json.dumps(dict(meta=meta, profils=res), indent=0))
for q in res[::8]:
    print(q, flush=True)
print("fini")
