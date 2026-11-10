#!/bin/bash
# À lancer sur la machine locale, détaché (nohup setsid). Attend la fin des calculs sur la machine
# AWS, rapatrie tous les cas, les traite, met à jour le rapport, pousse sur GitHub, puis ARRÊTE
# la machine AWS (sans la supprimer : OpenFOAM reste compilé ; outils/aws/demarrer_machine.sh la
# relance) SEULEMENT si tous les cas ont été rapatriés et vérifiés.
#   outils/aws/finaliser_campagne.sh <id_instance> <ip> <campagne> "<message de commit>" <dossier_distant>:<niveau> ...
# Chaque dossier distant doit contenir ordre.txt et TERMINE en fin de calcul. Un cas dont la vitesse
# n'est pas 1 m/s est rangé avec le suffixe _U<vitesse> (resultat_U2.json, ...), sauf si cas.json
# donne son propre « suffixe » (niveau 2 : _N2_rangs8, ...). Les ronds sont
# traités en premier (référence des comparaisons). Journal : cfd_campagne/<campagne>/journal.txt
ID=$1; IP=$2; CAMP=$3; MSG=$4; shift 4
CLE=~/.ssh/openfoam-key.pem
cd "$(dirname "$0")/../.."
R=cfd_campagne/$CAMP; mkdir -p $R
J=$R/journal.txt
log() { echo "$(date '+%F %H:%M:%S') $*" | tee -a $J; }
distant() { ssh -i $CLE -o ConnectTimeout=20 ubuntu@$IP "$@" < /dev/null; }
temoins=$(for d in "$@"; do printf -- "-f %s/TERMINE -a " "${d%%:*}"; done)

log "attente de la fin des calculs ($ID, $IP) : $*"
until distant "test ${temoins% -a }" 2>/dev/null; do
  etat=$(aws ec2 describe-instances --instance-ids $ID --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
  [ "$etat" != "running" ] && { log "ARRÊT : machine dans l'état « $etat », rien n'a été rapatrié"; exit 1; }
  sleep 300
done
log "calculs terminés, rapatriement"
ok=1
for d in "$@"; do
  dist=${d%%:*}; niv=${d##*:}
  mkdir -p $R/$niv
  distant "cd $dist && tar czf - --exclude='processor*' --exclude='VTK*' \$(cat ordre.txt) journal*.txt" | tar xzf - -C $R/$niv \
    || { log "ÉCHEC du rapatriement de $dist"; ok=0; }
  for c in $(distant "cat $dist/ordre.txt" | sort -t_ -k1,1 | awk '/^rond/{print; next}{a[n++]=$0} END{for(i=0;i<n;i++)print a[i]}'); do
    if grep -q '^End' $R/$niv/$c/log.pimpleFoam* 2>/dev/null && [ -f $R/$niv/$c/cas.json ]; then
      suf=$(.venv/bin/python -c "import json;m=json.load(open('$R/$niv/$c/cas.json'));U=m['U'];print(m.get('suffixe') or ('' if abs(U-1)<1e-9 else f'_U{U:g}'))")
      outils/cfd_2d/traiter_cas.sh $R/$niv/$c $niv $suf >> $J 2>&1 || { log "ÉCHEC du traitement de $c"; ok=0; }
    else
      log "INCOMPLET : $niv/$c"; ok=0
    fi
  done
done
.venv/bin/python outils/cfd_2d/rapport_pdf.py >> $J 2>&1
git add docs/formes docs/resultats_cfd.pdf resultats_cfd >> $J 2>&1
git commit -qm "$MSG

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" >> $J 2>&1 && git push -q origin HEAD >> $J 2>&1 && log "poussé sur GitHub"
if [ $ok = 1 ]; then
  for d in "$@"; do distant "rm -rf ${d%%:*}" 2>/dev/null; done   # libère le disque (cas rapatriés)
  aws ec2 stop-instances --instance-ids $ID --query 'StoppingInstances[0].CurrentState.Name' --output text >> $J 2>&1
  log "machine AWS $ID arrêtée (conservée, OpenFOAM compilé)"
else
  log "machine AWS CONSERVÉE (rapatriement ou traitement incomplet) : à vérifier"
fi
log "FIN"
