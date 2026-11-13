#!/bin/bash
# Rapatrie un cas terminé depuis la machine de calcul, le traite (outils/cfd_2d/traiter_cas.sh)
# et régénère docs/resultats_cfd.pdf.
#   outils/aws/rapatrier_forme.sh <forme> [ip] [dossier distant] [niveau]
set -e
F=$1; IP=${2:-100.31.204.54}; DIST=${3:-cas}; NIV=${4:-niveau1}
CLE=~/.ssh/openfoam-key.pem
cd "$(dirname "$0")/../.."
ssh -i $CLE ubuntu@$IP "grep -q '^End' $DIST/$F/log.pimpleFoam" < /dev/null || { echo "$F : pas terminé"; exit 1; }
D=cfd_campagne/${NIV}_resultats
mkdir -p $D && rm -rf $D/$F
ssh -i $CLE ubuntu@$IP "cd $DIST && tar czf - --exclude='processor*' $F" < /dev/null | tar xzf - -C $D
outils/cfd_2d/traiter_cas.sh $D/$F $NIV
../.venv/bin/python outils/cfd_2d/rapport_pdf.py > /dev/null
