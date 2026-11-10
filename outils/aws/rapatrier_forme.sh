#!/bin/bash
# Rapatrie un cas terminé depuis la machine de calcul, extrait les résultats, fait la figure,
# range le tout dans docs/formes/<forme>/, archive le cas et régénère docs/resultats_cfd.pdf.
#   outils/aws/rapatrier_forme.sh <forme> [ip] [niveau]
set -e
F=$1; IP=${2:-100.31.204.54}; NIV=${3:-niveau1}
CLE=~/.ssh/openfoam-key.pem
cd "$(dirname "$0")/../.."
ssh -i $CLE ubuntu@$IP "grep -q '^End' cas/$F/log.pimpleFoam" < /dev/null || { echo "$F : pas terminé"; exit 1; }
D=cfd_campagne/${NIV}_resultats
mkdir -p $D docs/formes/$F resultats_cfd/$NIV
rm -rf $D/$F
ssh -i $CLE ubuntu@$IP "cd cas && tar czf - --exclude='processor*' $F" < /dev/null | tar xzf - -C $D
.venv/bin/python outils/cfd_2d/extraire.py $D/$F --json $D/$F/resultat.json > /dev/null
( set +e; source /usr/lib/openfoam/openfoam2412/etc/bashrc >/dev/null 2>&1; set -e
  cd $D/$F && foamToVTK -latestTime -fields '(U T p UMean TMean pMean)' -name VTK_resultats > log.vtk 2>&1 )
.venv/bin/python outils/cfd_2d/figure_resultat.py $D/$F docs/formes/$F/resultat.png
.venv/bin/python -c "
import json; c='$D/$F/'
json.dump(dict(parametres=json.load(open(c+'cas.json')), resultats=json.load(open(c+'resultat.json'))),
          open('docs/formes/$F/resultat.json','w'), indent=1, ensure_ascii=False)"
.venv/bin/python outils/cfd_2d/archiver.py $D/$F resultats_cfd/$NIV/$F.tar.xz
.venv/bin/python outils/cfd_2d/rapport_pdf.py > /dev/null
.venv/bin/python -c "
import json; r=json.load(open('docs/formes/$F/resultat.json'))['resultats']
print(f\"$F : dp {r['dp_Pa']:.2f} Pa, efficacité {100*r['T_sortie']:.1f} %, h {r['h']:.1f}, stabilité ±{100*max(r['stabilite_moyenne'].values()):.1f} %, bilan {100*r['ecart_bilan']:+.2f} %\")"
