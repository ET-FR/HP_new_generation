#!/usr/bin/env python3
"""
Archive compacte d'un cas terminé, pour le conserver dans le dépôt (le conteneur cloud est temporaire).

Contenu : cas complet relançable (0/, system/, constant/ avec le maillage), dernier pas de temps
(champs instantanés et moyennés), postProcessing (séries temporelles), cas.json, resultat.json,
fin des journaux. Exclus : processor*, VTK*, pas de temps intermédiaires, journaux complets.

    python archiver.py dossier_du_cas resultats_cfd/niveau0/plaques.tar.xz
"""
import sys
import tarfile
from pathlib import Path


def dernier_temps(cas: Path):
    t = [p for p in cas.iterdir() if p.is_dir() and p.name.replace(".", "", 1).isdigit() and p.name != "0"]
    return max(t, key=lambda p: float(p.name)) if t else None


def archiver(cas, sortie):
    cas = Path(cas)
    Path(sortie).parent.mkdir(parents=True, exist_ok=True)
    garder = [cas / n for n in ("0", "system", "constant", "postProcessing", "cas.json", "resultat.json", "Allrun")]
    t = dernier_temps(cas)
    if t:
        garder.append(t)
    with tarfile.open(sortie, "w:xz", preset=9) as tar:
        for p in garder:
            if p.exists():
                tar.add(p, arcname=f"{cas.name}/{p.name}")
        for log in cas.glob("log.*"):
            lignes = log.read_text(errors="replace").splitlines()
            texte = "\n".join(lignes[:60] + ["[...]"] + lignes[-200:]) if len(lignes) > 300 else "\n".join(lignes)
            info = tarfile.TarInfo(f"{cas.name}/journaux/{log.name}")
            data = texte.encode()
            info.size = len(data)
            import io
            tar.addfile(info, io.BytesIO(data))
    return Path(sortie).stat().st_size


if __name__ == "__main__":
    print(f"{sys.argv[2]} : {archiver(sys.argv[1], sys.argv[2]) / 1e6:.1f} Mo")
