#!/bin/bash -e

{% set hostname = opts.get('hostname', 'saltmaster') -%}
{% set env = opts.get('environment', 'development') -%}
{% set index = opts.get('index', 1) -%}
{% set location = opts.get('location', 'ec2') -%}
{% set roles = opts.get('roles', ['salt.master']) -%}
{% set priv_key = opts.get('priv_key', '') -%}
{% set pub_key = opts.get('pub_key', '') -%}

echo "------> Bootstrapping master for environment {{ env }}"

__apt_get_noinput() {
    apt-get install -y -o DPkg::Options::=--force-confold $@
}

mkdir -p /etc/salt/pki

## Set keys
echo '{{ priv_key }}' > /etc/salt/pki/minion.pem
echo '{{ pub_key }}' > /etc/salt/pki/minion.pub

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
  environment: {{ env }}
  location: {{ location }}
""" > /etc/salt/master


echo """
### This is controlled by the hosts file
master: saltmaster

id: saltmaster

grains:
  environment: {{ env }}
  location: {{ location }}

log_file: /var/log/salt/minion
log_level: debug
log_level_logfile: garbage
""" > /etc/salt/minion

echo """
roles:
{% for role in roles -%}
  - {{ role }}
{% endfor -%}
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

apt-get update -y
__apt_get_noinput python-software-properties curl debconf-utils

(
  exec curl -L http://bootstrap.saltstack.org | sudo sh -s -- -M stable
)
