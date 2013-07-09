#!/bin/bash -ex

HOSTNAME=${1:-master}
SALT_MASTER=${2:-127.0.0.1}
ENV=${3:-development}
INDEX=${4:-1}
ROLES=${5:-saltmaster}

echo "------> Bootstrapping master for environment $ENV"

__apt_get_noinput() {
    apt-get install -y -o DPkg::Options::=--force-confold $@
}

apt-get update -y
__apt_get_noinput python-software-properties curl debconf-utils

# We're using the saltstack canonical bootstrap method here to stay with the
# latest open-source efforts

service salt-master stop || true
service salt-minion stop || true

# We're using the saltstack canonical bootstrap method here to stay with the
# latest open-source efforts
#
# Eventually, we can come to settle down on our own way of bootstrapping
(
  exec curl -L http://bootstrap.saltstack.org | sudo sh -s -- -M stable
)
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
    - saltmaster
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

log_file: /var/log/salt/minion
log_level: debug
log_level_logfile: garbage
""" > /etc/salt/minion

echo """
roles:
  - saltmaster
index: 1
""" > /etc/salt/grains

echo """# salt-master.conf
description 'salt-master upstart daemon'

start on (net-device-up
          and local-filesystems
          and runlevel [2345])
stop on runlevel [!2345]
limit nofile 100000 100000

respawn
respawn limit 5 20

script
exec salt-master
end script
""" > /etc/init/salt-master.conf

echo """# salt-minion.conf
description 'salt-minion upstart daemon'

start on (net-device-up
          and local-filesystems
          and runlevel [2345])
stop on runlevel [!2345]
limit nofile 100000 100000

respawn
respawn limit 5 20

script
exec salt-minion
end script

""" > /etc/init/salt-minion.conf

service salt-minion restart || service salt-minion start || true

salt-key -a saltmaster