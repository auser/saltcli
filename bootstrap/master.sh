#!/bin/bash -e
# sudo("/tmp/{script} {inst_name} {master_server} {env} {index} {rs}".format(

HOSTNAME=${1:-master}
SALT_MASTER=${2:-127.0.0.1}
ENV=${3:-development}
INDEX=${4:-1}
ROLES=${5:-master}

echo "------> Bootstrapping master for environment $ENV"

__apt_get_noinput() {
    apt-get install -y -o DPkg::Options::=--force-confold $@
}

apt-get update
__apt_get_noinput python-software-properties curl debconf-utils
apt-get update

# We're using the saltstack canonical bootstrap method here to stay with the
# latest open-source efforts
#
# Eventually, we can come to settle down on our own way of bootstrapping
\curl -L http://bootstrap.saltstack.org | sudo sh -s -- -M stable

# Set the hostname
echo """
127.0.0.1       localhost   saltmaster
""" > /etc/hosts
echo "saltmaster" > /etc/hostname
hostname `cat /etc/hostname`
mkdir -p /etc/salt

echo """
run_as: root

open_mode: False
auto_accept: False

worker_threads: 5

file_roots:
  base:
    - /srv/salt/states
  development:
    - /srv/salt/states/env/development
  staging:
    - /srv/salt/states/env/staging
  production:
    - /srv/salt/states/env/production

pillar_roots:
  base:
    - /srv/salt/pillar
  development:
    - /srv/salt/pillar/development
  staging:
    - /srv/salt/pillar/staging
  production:
    - /srv/salt/pillar/production

peer:
  .*:
    - network.ip_addrs
    - grains.*

master: 127.0.0.1
grains:
  roles: 
    - master
  environment: $ENV
  location: $LOC
""" > /etc/salt/master


echo """
### This is controlled by the hosts file
master: saltmaster

id: saltmaster

grains:
  environment: $ENV
  location: $LOC
  roles: 
    - master

log_file: /var/log/salt/minion
log_level: debug
log_level_logfile: garbage
""" > /etc/salt/minion

echo """
roles:
  - master
index: 1
""" > /etc/salt/grains

echo """
# salt-minion.conf
description 'salt-minion upstart daemon'
 
start on (net-device-up and local-filesystems)
stop on shutdown
 
expect fork
respawn
respawn limit 5 20
 
exec salt-minion -d
""" > /etc/init/salt-minion.conf

sudo restart salt-minion
sleep 15
sudo salt-key -a saltmaster
sudo salt-key -a `hostname`

sudo restart salt-master
