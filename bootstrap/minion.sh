#!/bin/bash -ex

{% set hostname = opts.get('hostname', 'minion') -%}
{% set saltmaster = opts.get('saltmaster', '192.168.1.11') -%}
{% set env = opts.get('environment', 'development') -%}
{% set index = opts.get('index', 1) -%}
{% set location = opts.get('location', 'ec2') -%}
{% set roles = opts.get('roles', ['salt.minion']) -%}
{% set priv_key = opts.get('priv_key', '') -%}
{% set pub_key = opts.get('pub_key', '') -%}

echo "------> Bootstrapping minion {{ hostname }} (master: {{ saltmaster }}) for environment {{ env }}"

mkdir -p /etc/salt/pki

## Set keys
echo '{{ priv_key }}' > /etc/salt/pki/minion.pem
echo '{{ pub_key }}' > /etc/salt/pki/minion.pub

# Set the hostname
echo """
127.0.0.1       localhost
127.0.1.1       {{ hostname }}
{{ saltmaster }}    saltmaster
""" > /etc/hosts
echo "{{ hostname }}" > /etc/hostname
hostname `cat /etc/hostname`

# Set salt master location and start minion
echo """
master: saltmaster
id: {{ hostname }}
log_file: /var/log/salt/minion
log_level: debug
log_fmt_logfile: '%(asctime)-15s salt-minion[%(process)d] %(name)s: %(message)s'
log_datefmt_logfile: '%b %d %H:%M:%S'
grains:
  environment: {{ env }}
  location: {{ location }}
  index: {{ index }}
mine_functions:
  network.ip_addrs:
    - eth0
    - eth1
  disk.usage: []
  grains.item:
    - index
    - roles
    - ec2_info
    - ec2_local-ipv4
""" > /etc/salt/minion

echo """
roles:
{% for role in roles -%}
  - {{ role }}
{% endfor -%}
""" > /etc/salt/grains

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

echo deb http://ppa.launchpad.net/saltstack/salt/ubuntu `lsb_release -sc` main | sudo tee /etc/apt/sources.list.d/saltstack.list
wget -q -O- "http://keyserver.ubuntu.com:11371/pks/lookup?op=get&search=0x4759FA960E27C0A6" | sudo apt-key add -

apt-get update -y
exec curl -L http://bootstrap.saltstack.org | sudo sh -s -- stable