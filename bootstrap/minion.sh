#!/bin/bash -ex

{% set hostname = opts.get('hostname', 'minion') -%}
{% set saltmaster = opts.get('saltmaster', '192.168.1.11') -%}
{% set env = opts.get('environment', 'development') -%}
{% set index = opts.get('index', 1) -%}
{% set roles = opts.get('roles', ['salt.minion']) -%}

echo "------> Bootstrapping minion {{ hostname }} (master: {{ saltmaster }}) for environment {{ env }}"

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
grains:
  environment: {{ env }}
  index: {{ index }}
""" > /etc/salt/minion

echo """
roles:
{% for role in roles -%}
  - {{ role }}
{% endfor -%}
""" > /etc/salt/grains

apt-get update
apt-get install -y -o DPkg::Options::=--force-confold salt-minion
