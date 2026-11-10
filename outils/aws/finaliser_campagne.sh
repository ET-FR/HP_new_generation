#!/bin/bash
# À lancer sur la machine locale, détaché (nohup setsid). Attend la fin des calculs sur la machine
# AWS, rapatrie tous les cas, les traite, met à jour le rapport, pousse sur GitHub, puis supprime
# la machine AWS SEULEMENT si tous les cas ont été rapatriés et vérifiés.
#   outils/aws/finaliser_campagne.sh <id_instance> <ip>
ID=$1; IP=$2
CLE=~/.ssh/openfoam-key.pem
cd "$(dirname "$0")/../.."
R=cfd_campagne/aws_final; mkdir -p $R
J=$R/journal.txt
log() { echo "$(date '+%F %H:%M:%S') $*" | tee -a $J; }
distant() { ssh -i $CLE -o ConnectTimeout=20 ubuntu@$IP "$@" < /dev/null; }

log "attente de la fin des calculs ($ID, $IP)"
until distant 'test -f cas2/TERMINE -a -f cas/PROLONGATION_TERMINEE' 2>/dev/null; do
  etat=$(aws ec2 describe-instances --instance-ids $ID --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
  [ "$etat" != "running" ] && { log "ARRÊT : machine dans l'état « $etat », rien n'a été rapatrié"; exit 1; }
  sleep 300
done
log "calculs terminés, rapatriement"
ok=1
for d in cas:niveau1 cas2:serie2; do
  dist=${d%%:*}; niv=${d##*:}
  mkdir -p $R/$niv
  distant "cd $dist && tar czf - --exclude='processor*' --exclude='VTK*' \$(cat ordre.txt) journal*.txt" | tar xzf - -C $R/$niv \
    || { log "ÉCHEC du rapatriement de $dist"; ok=0; }
  for c in $(distant "cat $dist/ordre.txt"); do
    if grep -q '^End' $R/$niv/$c/log.pimpleFoam* 2>/dev/null && [ -f $R/$niv/$c/cas.json ]; then
      outils/cfd_2d/traiter_cas.sh $R/$niv/$c $niv >> $J 2>&1 || { log "ÉCHEC du traitement de $c"; ok=0; }
    else
      log "INCOMPLET : $niv/$c"; ok=0
    fi
  done
done
.venv/bin/python outils/cfd_2d/rapport_pdf.py >> $J 2>&1
git add docs/formes docs/resultats_cfd.pdf resultats_cfd >> $J 2>&1
git commit -qm "Campagne AWS terminée : niveau 1 prolongé et série 2 (22 formes), rapport mis à jour

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" >> $J 2>&1 && git push -q origin HEAD >> $J 2>&1 && log "poussé sur GitHub"
if [ $ok = 1 ]; then
  aws ec2 terminate-instances --instance-ids $ID --query 'TerminatingInstances[0].CurrentState.Name' --output text >> $J 2>&1
  log "machine AWS $ID supprimée"
else
  log "machine AWS CONSERVÉE (rapatriement ou traitement incomplet) : à vérifier"
fi
log "FIN"
