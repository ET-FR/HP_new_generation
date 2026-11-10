#!/bin/bash
# Sur la machine de calcul : lance tous les cas de ~/cas/ (un dossier par cas, avec Allrun),
# PARALLELES cas à la fois, puis écrit ~/cas/TERMINE. Journal : ~/cas/journal.txt
PARALLELES=${1:-4}
source /opt/openfoam/OpenFOAM-v2606/etc/bashrc >/dev/null 2>&1
export OMPI_MCA_rmaps_base_oversubscribe=1
cd ~/cas
un_cas() {
  c=$1; t=$(date +%s)
  echo "$(date +%H:%M:%S) début $c" >> journal.txt
  bash $c/Allrun; rc=$?
  echo "$(date +%H:%M:%S) fin $c rc=$rc durée=$(( $(date +%s)-t )) s" >> journal.txt
}
export -f un_cas
ls -d */ | tr -d / | xargs -P $PARALLELES -I{} bash -c 'un_cas {}'
echo "$(date +%H:%M:%S) TOUS LES CAS TERMINÉS" >> journal.txt
touch TERMINE
