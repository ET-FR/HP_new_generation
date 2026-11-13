#!/usr/bin/env python3
"""
Campagne CFD : crée et exécute les cas (surface × Re), puis extrait j et f.

    source /usr/lib/openfoam/openfoam2412/etc/bashrc
    python conception_echangeur/outils/cfd_tpms/lancer_campagne.py --dossier cfd_campagne \
        --surfaces gyroide diamond fks iwp primitive --Re 100 200 400 800 1600

Les cas déjà terminés (log.simpleFoam se terminant par « End ») ne sont pas relancés :
on peut interrompre et reprendre. --paralleles cas tournent en même temps, chacun sur
--nproc cœurs (8 cœurs : 2 × 4 par défaut).
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from creer_cas import creer_cas  # noqa: E402
import extraire  # noqa: E402


def nom_cas(surface, Re, phi, finesse, raff, profondeur):
    return f"{surface}_phi{phi:.2f}_D{profondeur:g}_Re{Re:g}_m{finesse}r{raff}"


def termine(d: Path) -> bool:
    log = d / "log.simpleFoam"
    return log.exists() and "End" in log.read_text(errors="replace")[-2000:]


def executer(d: Path) -> tuple[str, float, bool]:
    t0 = time.time()
    r = subprocess.run(["bash", str(d / "Allrun")], cwd=d)
    if (d / "processor0").exists() and termine(d):
        for p in d.glob("processor*"):      # place disque : les résultats sont dans postProcessing
            shutil.rmtree(p, ignore_errors=True)
    return d.name, time.time() - t0, r.returncode == 0 and termine(d)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dossier", required=True)
    ap.add_argument("--surfaces", nargs="+", default=["gyroide", "diamond", "fks", "iwp", "primitive"])
    ap.add_argument("--Re", nargs="+", type=float, default=[100, 200, 400, 800, 1600])
    ap.add_argument("--phi", nargs="+", type=float, default=[0.6])
    ap.add_argument("--Dh", type=float, default=4.0)
    ap.add_argument("--profondeur", type=float, default=24.0)
    ap.add_argument("--finesse", type=int, default=8)
    ap.add_argument("--raffinement", type=int, default=2)
    ap.add_argument("--nproc", type=int, default=4)
    ap.add_argument("--paralleles", type=int, default=2)
    ap.add_argument("--iterations", type=int, default=3000)
    ap.add_argument("--creer-seulement", action="store_true")
    a = ap.parse_args()
    if not shutil.which("simpleFoam") and not a.creer_seulement:
        sys.exit("OpenFOAM introuvable : source /usr/lib/openfoam/openfoam2412/etc/bashrc")

    racine = Path(a.dossier).resolve()
    racine.mkdir(parents=True, exist_ok=True)
    a_lancer, tous = [], []
    for s in a.surfaces:
        for phi in a.phi:
            for Re in a.Re:
                d = racine / nom_cas(s, Re, phi, a.finesse, a.raffinement, a.profondeur)
                tous.append(d)
                if termine(d):
                    continue
                if not (d / "Allrun").exists():
                    creer_cas(s, phi, Re, a.Dh, a.profondeur, d, a.finesse, a.raffinement, a.nproc, a.iterations)
                a_lancer.append(d)
    print(f"{len(tous)} cas, {len(a_lancer)} à calculer")
    if a.creer_seulement or not a_lancer:
        pass
    else:
        with ThreadPoolExecutor(max_workers=a.paralleles) as ex:
            for nom, duree, ok in ex.map(executer, a_lancer):
                print(f"{'ok ' if ok else 'ÉCHEC'} {nom}  ({duree / 60:.1f} min)", flush=True)
    os.chdir(racine)
    extraire.main([d.name for d in tous if (d / "postProcessing").exists()])


if __name__ == "__main__":
    main()
