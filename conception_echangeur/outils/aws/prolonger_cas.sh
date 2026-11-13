#!/bin/bash
# Sur la machine de calcul : prolonge des cas instationnaires terminés (reprise au dernier pas de
# temps), en ajoutant FACTEUR × la durée de la fenêtre de moyenne actuelle. 4 cas en parallèle.
#   ./prolonger_cas.sh DOSSIER FACTEUR ATTENDRE cas1 cas2 ...
#   (ATTENDRE : fichier dont on attend l'apparition avant de commencer, ou « - »)
DOSSIER=$1; FACTEUR=$2; ATTENDRE=$3; shift 3
[ "$ATTENDRE" != "-" ] && until [ -f "$ATTENDRE" ]; do sleep 60; done
source /opt/openfoam/OpenFOAM-v2606/etc/bashrc >/dev/null 2>&1
export OMPI_MCA_rmaps_base_oversubscribe=1
cd $DOSSIER
prolonger() {
  c=$1; t=$(date +%s)
  echo "$(date +%H:%M:%S) début prolongation $c" >> journal_prolongation.txt
  fin=$(python3 -c "
import json; m=json.load(open('$c/cas.json')); f=m['fin']+$FACTEUR*(m['fin']-m['debut_moyenne'])
m['fin_initiale']=m.get('fin_initiale',m['fin']); m['fin']=round(f,4); json.dump(m,open('$c/cas.json','w'),indent=1,ensure_ascii=False); print(m['fin'])")
  sed -i "s/^endTime .*/endTime         $fin;/" $c/system/controlDict
  ( cd $c && mpirun -np 4 pimpleFoam -parallel > log.pimpleFoam_prolongation 2>&1 && reconstructPar -newTimes > log.reconstructPar_prolongation 2>&1 )
  echo "$(date +%H:%M:%S) fin prolongation $c rc=$? jusqu'à t=$fin s durée=$(( $(date +%s)-t )) s" >> journal_prolongation.txt
}
export -f prolonger; export FACTEUR
printf "%s\n" "$@" | xargs -P 4 -I{} bash -c 'prolonger {}'
touch PROLONGATION_TERMINEE
