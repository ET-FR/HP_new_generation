#!/bin/bash
# Redémarre la machine de calcul conservée (OpenFOAM v2606 déjà compilé dans /opt/openfoam),
# arme un arrêt de sécurité, et affiche son adresse IP (elle change à chaque démarrage).
#   outils/aws/demarrer_machine.sh [id_instance] [type]   (type : change la taille si la machine est arrêtée,
#                                                          ex. c7a.12xlarge = 48 cœurs, c7a.16xlarge = 64)
# Machine arrêtée : seul le disque est facturé (60 Go gp3 ≈ 5 $/mois).
ID=${1:-$(aws ec2 describe-instances --filters Name=tag:role,Values=calcul-cfd-reutilisable \
          Name=instance-state-name,Values=stopped,running --query 'Reservations[0].Instances[0].InstanceId' --output text)}
TYPE=$2
DUREE_MAX=${DUREE_MAX:-480}      # minutes avant arrêt de sécurité
K=~/.ssh/openfoam-key.pem
[ "$ID" = None ] && { echo "aucune machine conservée (tag role=calcul-cfd-reutilisable)"; exit 1; }
etat=$(aws ec2 describe-instances --instance-ids $ID --query 'Reservations[0].Instances[0].State.Name' --output text)
if [ -n "$TYPE" ] && [ "$etat" = stopped ]; then
  aws ec2 modify-instance-attribute --instance-id $ID --instance-type Value=$TYPE || exit 1
fi
[ "$etat" != running ] && aws ec2 start-instances --instance-ids $ID > /dev/null
aws ec2 wait instance-running --instance-ids $ID
IP=$(aws ec2 describe-instances --instance-ids $ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)
for i in $(seq 40); do
  timeout 15 ssh -i $K -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 ubuntu@$IP true < /dev/null 2>/dev/null && break
  timeout 5 tail -f /dev/null
done
ssh -i $K ubuntu@$IP "sudo shutdown -h +$DUREE_MAX 'Arrêt de sécurité' 2>/dev/null; test -f ~/OPENFOAM_PRET && echo 'OpenFOAM prêt' || echo 'OpenFOAM ABSENT'" < /dev/null
echo "$ID $IP"
