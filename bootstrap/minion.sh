#!/bin/bash -ex

HOSTNAME=${1:-minion}
SALT_MASTER=${2:-192.168.98.11}
ENV=${3:-development}
INDEX=${4:-1}
ROLES=${5:-salt.minion}

echo "------> Bootstrapping minion $HOSTNAME (master: $SALT_MASTER) for environment $ENV"
echo "--------> Roles: $ROLES"

__apt_get_noinput() {
    apt-get install -y -o DPkg::Options::=--force-confold $@
}

apt-get update
__apt_get_noinput python-software-properties curl debconf-utils
apt-get update

# Set the hostname
echo """
127.0.0.1       localhost
127.0.1.1       $HOSTNAME
$SALT_MASTER    saltmaster
""" > /etc/hosts
echo "$HOSTNAME" > /etc/hostname
hostname `cat /etc/hostname`

# We're using the saltstack canonical bootstrap method here to stay with the
# latest open-source efforts

pkill salt-minion || true

# Eventually, we can come to settle down on our own way of bootstrapping
(
  curl -L http://bootstrap.saltstack.org | sudo sh -s -- stable
)

# Set salt master location and start minion
echo """
master: saltmaster
id: $HOSTNAME
grains:
  environment: $ENV
  index: $INDEX
""" > /etc/salt/minion

echo """
environment: $ENV
index: $INDEX
roles:
""" > /etc/salt/grains

for i in $(echo "$ROLES" | tr "," "\n")
do
  echo "  - ${i}" >> /etc/salt/grains
done
