#!/bin/bash
# Démarrage d'une machine de calcul EC2 (Ubuntu 24.04) : compile OpenFOAM v2606 (ESI) dans
# /opt/openfoam, puis écrit /home/ubuntu/OPENFOAM_PRET.
# Sécurité : arrêt automatique (= suppression si le comportement d'arrêt est « terminate »)
# au bout de DUREE_MAX minutes, même si rien n'est fini.
DUREE_MAX=480
shutdown -h +$DUREE_MAX "Arrêt de sécurité : durée maximale atteinte"
exec > /var/log/openfoam_install.log 2>&1
set -x
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq build-essential flex libfl-dev bison zlib1g-dev libopenmpi-dev openmpi-bin \
    cmake libscotch-dev libptscotch-dev libfftw3-dev libreadline-dev libncurses-dev libgmp-dev \
    libmpfr-dev curl python3-numpy
mkdir -p /opt/openfoam && cd /opt/openfoam
curl -sSL -o OpenFOAM-v2606.tgz "https://sourceforge.net/projects/openfoam/files/v2606/OpenFOAM-v2606.tgz/download"
tar xzf OpenFOAM-v2606.tgz
cd OpenFOAM-v2606
sed -i 's/^SCOTCH_VERSION=.*/SCOTCH_VERSION=scotch-system/; s|^export SCOTCH_ARCH_PATH=.*|export SCOTCH_ARCH_PATH=/usr|' etc/config.sh/scotch
set +x
source etc/bashrc
set -x
export WM_NCOMPPROCS=$(nproc)
t=$(date +%s)
./Allwmake -j $(nproc) -s -l > /home/ubuntu/log.Allwmake 2>&1
echo "compilation : $(( ($(date +%s)-t)/60 )) min" >> /home/ubuntu/log.Allwmake
chown -R ubuntu:ubuntu /opt/openfoam
if [ -x platforms/linux64GccDPInt32Opt/bin/pimpleFoam ]; then
  echo "v2606 prête" > /home/ubuntu/OPENFOAM_PRET
else
  echo "échec de compilation" > /home/ubuntu/OPENFOAM_ECHEC
fi
