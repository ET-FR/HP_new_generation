#!/bin/bash
# Compile OpenFOAM v2606 (ESI / openfoam.com) depuis les sources, sur Ubuntu 24.04.
# Utilisé dans le conteneur cloud et prévu pour une machine AWS. Durée : 2 à 3 h sur 4 cœurs.
#
#   sudo bash outils/openfoam/installer_v2606.sh [/opt/openfoam] [nombre_de_coeurs]
#   source /opt/openfoam/OpenFOAM-v2606/etc/bashrc
#
# Choix : MPI et Scotch du système (paquets Ubuntu), pas de ThirdParty (non nécessaire
# pour nos cas : simpleFoam, pimpleFoam, snappyHexMesh, gmshToFoam, découpage scotch).
set -euo pipefail
DEST=${1:-/opt/openfoam}
NP=${2:-$(nproc)}

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential flex libfl-dev bison zlib1g-dev libopenmpi-dev openmpi-bin \
    cmake libscotch-dev libptscotch-dev libfftw3-dev libreadline-dev libncurses-dev libgmp-dev libmpfr-dev curl

mkdir -p "$DEST" && cd "$DEST"
[ -f OpenFOAM-v2606.tgz ] || curl -sSL -o OpenFOAM-v2606.tgz \
    "https://sourceforge.net/projects/openfoam/files/v2606/OpenFOAM-v2606.tgz/download"
[ -d OpenFOAM-v2606 ] || tar xzf OpenFOAM-v2606.tgz
cd OpenFOAM-v2606

# Scotch du système
sed -i 's/^SCOTCH_VERSION=.*/SCOTCH_VERSION=scotch-system/; s|^export SCOTCH_ARCH_PATH=.*|export SCOTCH_ARCH_PATH=/usr|' \
    etc/config.sh/scotch

set +u
source etc/bashrc || true
set -u
foamSystemCheck
export WM_NCOMPPROCS=$NP
./Allwmake -j "$NP" -s -q -l
echo "Installation terminée : source $DEST/OpenFOAM-v2606/etc/bashrc"
