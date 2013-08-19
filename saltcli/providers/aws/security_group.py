import os, sys, base64
import boto, boto.ec2
import time
from stat import *
import xml.etree.ElementTree as ET
from saltcli.utils.utils import get_colors
from saltcli.providers import Provider, dict_merge
from saltcli.models.instance import Instance
from saltcli.providers.aws.keypair import setup_keypair, key_name, key_filename
import collections

SecurityGroupRule = collections.namedtuple("SecurityGroupRule", ["ip_protocol", "from_port", "to_port", "cidr_ip", "src_group_name"])

def setup_security_group(conn, instance, provider, launch_config):
  ## Now that we have our connection...
  environment = instance.environment
  config = provider.config
  group_name = _group_name(conn, instance, config)
  groups = [g for g in conn.get_all_security_groups() if g.name == group_name]
  group = groups[0] if groups else None
  if not group:
    instance.environment.debug("Creating group '%s'..."%(group_name,))
    group = conn.create_security_group(group_name, "A group for %s"%(group_name,))

  expected_rules = []

  if 'allow_groups' in launch_config:
    allow_groups_names = launch_config['allow_groups']
    # If we want ALL groups
    if allow_groups_names == '*':
      allow_groups_names = config['machines'].keys()

    ## This is a dirty way of looking up all groups
    allow_groups = []
    for name in allow_groups_names:
      if name != 'default':
        launch_config_for_machine = provider._load_machine_desc(name)
        if 'region' in launch_config_for_machine:
          this_conn = provider._load_connection_for_region(launch_config_for_machine['region'])
        elif provider.config['region'] != conn.region:
          this_conn = provider._load_connection_for_region(provider.config['region'])
          
        gn = key_name(this_conn, config)+"-"+provider.environment.environment+'-'+name
        if gn != group_name:
          allow_groups.append(gn)
  
  if 'ports' in launch_config:
    for proto, port_conf in launch_config['ports'].iteritems():
      for cidr, ports in port_conf.iteritems():
        for port in ports:
          rule = SecurityGroupRule(str(proto), str(port), str(port), str(cidr), None)
          expected_rules.append(rule)
  
  # for g in self.conn.get_all_security_groups():
    # expected_rules.append(SecurityGroupRule('tcp', 22, 65535, '0.0.0.0/0', g.name))
  
  colors = get_colors()
  if environment.opts.get('answer_yes', False):
    environment.info('''{0}Updating security group to match the configuration for group {2}{1[ENDC]}'''.format(colors['RED'], colors, group_name))
    current_rules = []
    for rule in group.rules:
      if not rule.grants[0].cidr_ip:
        current_rule = SecurityGroupRule(str(rule.ip_protocol),
                          str(rule.from_port),
                          str(rule.to_port),
                          "0.0.0.0/0",
                          str(rule.grants[0].name))
      else:
        current_rule = SecurityGroupRule(str(rule.ip_protocol),
                          str(rule.from_port),
                          str(rule.to_port),
                          str(rule.grants[0].cidr_ip),
                          None)
                          
      if current_rule not in expected_rules:
        _revoke(group, conn, current_rule)
      else:
        current_rules.append(current_rule)
          
    for rule in expected_rules:
      if rule not in current_rules:
        _authorize(group, conn, rule)

    ## Groups
    for name in allow_groups:
      src_group = get_or_create_security_group(conn, name)
      print "Authorizing group: %s"%(name,)
      try:
        group.authorize(src_group=src_group)
      except:
        ## EC2 hates it when you try to authorize the
        ## same rule twice.
        False

  else:
    environment.info('''{0}
      Not updating the security group authorizations for the group:
      {2}
      If you want to update the security group rules, pass `-y` option{1[ENDC]}
      '''.format(colors['BLUE'], colors, group_name))
  
  return group

def _modify_sg(conn, group, rule, authorize=False, revoke=False):
    src_group = None
    if rule.src_group_name:
      src_group = get_or_create_security_group(conn, rule.src_group_name)

    if authorize and not revoke:
        print "Authorizing missing rule %s..."%(rule,)
        group.authorize(ip_protocol=rule.ip_protocol,
                        from_port=str(rule.from_port),
                        to_port=str(rule.to_port),
                        cidr_ip=rule.cidr_ip,
                        src_group=src_group)
    elif not authorize and revoke:
        print "Revoking unexpected rule %s..."%(rule,)
        group.revoke(ip_protocol=rule.ip_protocol,
                     from_port=str(rule.from_port),
                     to_port=str(rule.to_port),
                     cidr_ip=rule.cidr_ip,
                     src_group=src_group)


def _authorize(group, conn, rule):
    """Authorize `rule` on `group`."""
    return _modify_sg(conn, group, rule, authorize=True)


def _revoke(group, conn, rule):
    """Revoke `rule` on `group`."""
    return _modify_sg(conn, group, rule, revoke=True)

def _group_name(conn, instance, config):
  return key_name(conn, config) + "-" + instance.instance_name

def get_or_create_security_group(conn, group_name, description=""):
    """
    """
    groups = [g for g in conn.get_all_security_groups() if g.name == group_name]
    group = groups[0] if groups else None
    if not group:
      group = conn.create_security_group(group_name, "A group for %s"%(group_name,))
    return group