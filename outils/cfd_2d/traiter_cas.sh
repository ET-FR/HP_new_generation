#!/bin/bash
# Traite un cas terminé déjà présent localement : extraction, figure, rangement dans
# docs/formes/<forme>/, archive dans resultats_cfd/<niveau>/.
#   outils/cfd_2d/traiter_cas.sh <dossier_du_cas> <niveau> [suffixe]
# suffixe (ex. _U2) : resultat<suffixe>.json/png et <forme><suffixe>.tar.xz, pour ne pas écraser
# le cas de référence à 1 m/s.
set -e
C=$1; NIV=$2; S=${3:-}
cd "$(dirname "$0")/../.."
F=$(.venv/bin/python -c "import json;print(json.load(open('$C/cas.json'))['forme'])")
mkdir -p docs/formes/$F resultats_cfd/$NIV
.venv/bin/python outils/cfd_2d/extraire.py $C --json $C/resultat.json > /dev/null
rm -rf $C/VTK_resultats
( set +e; source /usr/lib/openfoam/openfoam2412/etc/bashrc >/dev/null 2>&1; set -e
  cd $C && foamToVTK -latestTime -fields '(U T p UMean TMean pMean)' -name VTK_resultats > log.vtk 2>&1 )
.venv/bin/python outils/cfd_2d/figure_resultat.py $C docs/formes/$F/resultat$S.png
.venv/bin/python -c "
import json; c='$C/'
json.dump(dict(parametres=json.load(open(c+'cas.json')), resultats=json.load(open(c+'resultat.json'))),
          open('docs/formes/$F/resultat$S.json','w'), indent=1, ensure_ascii=False)
r=json.load(open(c+'resultat.json'))
print(f\"$F$S : dp {r['dp_Pa']:.2f} Pa, efficacité {100*r['T_sortie']:.1f} %, h {r['h']:.1f}, stabilité ±{100*max(r['stabilite_moyenne'].values()):.1f} %, bilan {100*r['ecart_bilan']:+.2f} %\")"
.venv/bin/python outils/cfd_2d/archiver.py $C resultats_cfd/$NIV/$F$S.tar.xz > /dev/null
