#!/bin/bash
# Sur la machine de calcul : lance tous les cas de DOSSIER (un dossier par cas, avec Allrun),
# PARALLELES cas à la fois, puis écrit DOSSIER/TERMINE. Journal : DOSSIER/journal.txt
#   ./lancer_cas.sh [PARALLELES] [DOSSIER] [ATTENDRE]   (ATTENDRE : fichier dont on attend l'apparition)
PARALLELES=${1:-4}
DOSSIER=${2:-~/cas}
ATTENDRE=${3:-}
[ -n "$ATTENDRE" ] && until [ -f "$ATTENDRE" ]; do sleep 60; done
# attend la fin de la compilation d'OpenFOAM (user_data_openfoam.sh)
until [ -f ~/OPENFOAM_PRET ] || [ -f ~/OPENFOAM_ECHEC ]; do sleep 30; done
[ -f ~/OPENFOAM_ECHEC ] && { echo "OpenFOAM non compilé" > $DOSSIER/ECHEC; exit 1; }
source /opt/openfoam/OpenFOAM-v2606/etc/bashrc >/dev/null 2>&1
export OMPI_MCA_rmaps_base_oversubscribe=1
# pas d'attache des processus MPI à des cœurs fixes : sinon, avec -np 2, OpenMPI attache CHAQUE calcul
# aux cœurs 0 et 1 et tous les cas parallèles s'y empilent (constaté le 10/11/2026 : 18 cas sur 2 cœurs)
export OMPI_MCA_hwloc_base_binding_policy=none
cd $DOSSIER
un_cas() {
  c=$1; t=$(date +%s)
  echo "$(date +%H:%M:%S) début $c" >> journal.txt
  bash $c/Allrun; rc=$?
  echo "$(date +%H:%M:%S) fin $c rc=$rc durée=$(( $(date +%s)-t )) s" >> journal.txt
}
export -f un_cas
# ordre.txt (facultatif) : un cas par ligne, les plus longs d'abord, pour finir au plus tôt
if [ -f ordre.txt ]; then cat ordre.txt; else ls -d */ | tr -d /; fi | xargs -P $PARALLELES -I{} bash -c 'un_cas {}'
echo "$(date +%H:%M:%S) TOUS LES CAS TERMINÉS" >> journal.txt
touch TERMINE
