import os, sys, base64
import boto
import time
import xml.etree.ElementTree as ET
from saltcli.utils.utils import get_colors
from saltcli.providers import Provider, dict_merge
import collections

SecurityGroupRule = collections.namedtuple("SecurityGroupRule", ["ip_protocol", "from_port", "to_port", "cidr_ip", "src_group_name"])

class Aws(Provider):
  def __init__(self, config):
    super(Aws, self).__init__(config)
    self._load_connection()
    
  ## Public methods
  def launch(self, instances):
    if not isinstance(instances, dict):
      instances = [instances]
    for name, inst in instances.iteritems():
      if inst.get():
        colors = get_colors()
        inst.environment.info("{0}Not launching {1}. It is already launched.{2[ENDC]}".format(colors['RED'], name, colors))
      else:
        instance = self.launch_single_instance(inst)
        self.ssh.wait_for_ssh(instance.ip_address(), instance.ssh_port())
    
  ## Launch a single instance
  def launch_single_instance(self, instance):
    launch_config = self._load_machine_desc(instance.name)
    ## RELOAD the ec2 connection based on a new region
    if launch_config['region'] != self.conn.region:
      self._load_connection(region=launch_config['region'])
    
    security_group = self._setup_security_group(instance, launch_config)
    keypair = self._setup_keypair(instance, launch_config)
    colors = get_colors()
    
    print """Launching an AWS instance:
    Image:          {color}{image_id}{colors[ENDC]}
    Keyname:        {color}{key_name}{colors[ENDC]}
    security_group: {color}{security_group}{colors[ENDC]}
    flavor:         {color}{flavor}{colors[ENDC]}
    placement:      {color}{placement}{colors[ENDC]}
    """.format(
      image_id=launch_config['image_id'],
      key_name=instance.keyname(),
      security_group=security_group.name,
      flavor=launch_config['flavor'],
      placement=self.conn.region,
      color=colors['YELLOW'],
      colors=colors
    )
    try:
      reservation = self.conn.run_instances(launch_config['image_id'], 
                              key_name=instance.keyname(),
                              security_groups=[security_group.name],
                              instance_type=launch_config['flavor'],
                              )
    except boto.exception.EC2ResponseError as e:
      print "Exception: {0}".format(e)
      if e.status == 400:
        sys.exit(-1)
    instance.environment.debug("{0}Launching...{1[ENDC]}".format(colors['GREEN'], colors))
    running_instance = reservation.instances[0] #### <~ ew
    # Check up on its status every so often
    instance.environment.debug("{0}Launched. Waiting for the instance to become available.{1[ENDC]}".format(colors['YELLOW'], colors))
    status = running_instance.update()
    while status == 'pending':
        time.sleep(10)
        status = running_instance.update()
    instance.environment.info("Instance {0} launched at {1}".format(running_instance.id, running_instance.ip_address))
    
    if status == 'running':
      running_instance.add_tag("name", instance.name)
      running_instance.add_tag('instance_name', instance.instance_name)
      running_instance.add_tag('environment', instance.environment.environment)
    else:
      print "Instance status: {0}".format(status)
      
    return instance
      
  
  def teardown(self, instance):
    """Teardown"""
    colors = get_colors()
    if instance:
      instance.environment.debug("{0}Tearing down instance: {1}{2[ENDC]}".format(
        colors['GREEN'], instance.instance_name, colors))
      self.conn.terminate_instances([instance.get().id])
      if not instance.ismaster():
        self.remove_minion_key(instance)
    else:
      instance.environment.debug("{0}Could not find instance by name {1}{2[ENDC]}".format(
        colors['RED'], instance.name, colors))
      
  def get(self, name):
    if isinstance(name, str):
      return self._get_by_name(name)
    elif isinstance(name, Instance):
      return self._get_by_name(name.instance_name)
    else:
      print name
      
  def _get_by_name(self, name):
    for inst in self.all():
      if name == inst.tags.get('instance_name', None):
        return inst
    return None
    
  def all(self):
    """List instances"""
    running_instances = []
    reservations = self.conn.get_all_instances()
    for res in reservations:
      for inst in res.instances:
        print "inst: {0}".format(inst)
        if inst.key_name == self.keypair_name() and inst.update() == 'running':
          running_instances.append(inst)
    return running_instances
    
  ## All the names of every instance
  def all_names(self):
    running_instance_names = []
    for i in self.all():
      running_instance_names.append(i.tags['name'])
    return running_instance_names
    
  # Set up the keypair
  # This will look at the key_filename
  def _setup_keypair(self, instance, launch_config):
    key_path = instance.key_filename()
    if self.keypair_name() in [k.name for k in self._all_keypairs()]:
      keypair = None
      for k in self._all_keypairs():
        if k.name == self.keypair_name():
          keypair = k
      if keypair:
        if keypair.region != self.conn.region:
          instance.environment.debug(
            "Keypair was created in a different region ({old}). Copying it to our current region {curr}".format(
              old=keypair.region.name,
              curr=self.conn.region,
            )
          )
          output = keypair.copy_to_region(self.conn.region)
          print "keypair: {0}".format(output)
    else:
      try:
        ## Attempting to create_key_pair
        key   = self.conn.create_key_pair(self.keypair_name())
        filepath = os.path.dirname(key_path)
        key.save(filepath)
        os.chmod(filepath, 644)
      except Exception, e:
        instance.environment.debug("Keypair exception '%s'..."%(e))
        True
    
    return self.keypair_name()
    
  ## ALL KEYPAIRS
  def _all_keypairs(self):
    return self.conn.get_all_key_pairs()
    
  # Convenience method to get the keypair
  def keypair_name(self):
    return self.config['keyname']
    
  ## Create the security group and attach the appropriate permissions
  def _setup_security_group(self, instance, launch_config):
    group_name = instance.keyname() + "-" + instance.instance_name
    groups = [g for g in self.conn.get_all_security_groups() if g.name == group_name]
    group = groups[0] if groups else None
    if not group:
      instance.environment.debug("Creating group '%s'..."%(group_name,))
      group = self.conn.create_security_group(group_name, "A group for %s"%(group_name,))
    
    expected_rules = []
    if 'ports' in launch_config:
      for proto, port_conf in launch_config['ports'].iteritems():
        for cidr, ports in port_conf.iteritems():
          for port in ports:
            rule = SecurityGroupRule(str(proto), str(port), str(port), str(cidr), None)
            expected_rules.append(rule)
    
    # for g in self.conn.get_all_security_groups():
      # expected_rules.append(SecurityGroupRule('tcp', 22, 65535, '0.0.0.0/0', g.name))
    
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
        self._revoke(group, current_rule)
      else:
        current_rules.append(current_rule)
          
    for rule in expected_rules:
      if rule not in current_rules:
        self._authorize(group, rule)
    
    return group
  
  def _modify_sg(self, group, rule, authorize=False, revoke=False):
      src_group = None
      if rule.src_group_name:
          src_group = self.conn.get_all_security_groups([rule.src_group_name,])[0]
 
      if authorize and not revoke:
          # print "Authorizing missing rule %s..."%(rule,)
          group.authorize(ip_protocol=rule.ip_protocol,
                          from_port=str(rule.from_port),
                          to_port=str(rule.to_port),
                          cidr_ip=rule.cidr_ip,
                          src_group=src_group)
      elif not authorize and revoke:
          # print "Revoking unexpected rule %s..."%(rule,)
          group.revoke(ip_protocol=rule.ip_protocol,
                       from_port=str(rule.from_port),
                       to_port=str(rule.to_port),
                       cidr_ip=rule.cidr_ip,
                       src_group=src_group)
 
 
  def _authorize(self, group, rule):
      """Authorize `rule` on `group`."""
      return self._modify_sg(group, rule, authorize=True)
 
 
  def _revoke(self, group, rule):
      """Revoke `rule` on `group`."""
      return self._modify_sg(group, rule, revoke=True)
  
  
  ## Setup connection
  def _load_connection(self, **kwargs):
    """Load connection"""
    self._load_credentials()
    if 'region' in kwargs:
      kwargs['region'] = boto.ec2.get_region(kwargs['region'])
    print "kwargs: {0}".format(kwargs)
    self.conn = boto.connect_ec2(self.access_key, self.secret_key, **kwargs)
    
  def _load_machine_desc(self, name):
    """Load machine descriptions"""
    machines = self.config['machines']
    default_aws_config = {
      'region': 'us-east-1',
    }
    default = dict_merge(machines['default'], default_aws_config)
    try:
      machine_config = dict_merge(machines[name], default)
    except Exception, e:
      print "EXCEPTION: {0}".format(e)
      machine_config = default
    
    return machine_config
    
  ## Load the aws credentials, either from the 
  ## config, or from the environment
  def _load_credentials(self):
    """Load credentials"""
    try:
      if 'access_key' in self.config:
        self.access_key = self.config['access_key']
      else:
        self.access_key = os.environ['AWS_ACCESS_KEY']
    except KeyError: 
      print "Please set the environment variable AWS_ACCESS_KEY"
      sys.exit(1)

    try:
      if 'secret_key' in self.config:
        self.secret_key = self.config['secret_key']
      else:
        self.secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
    except KeyError: 
      print "Please set the environment variable AWS_SECRET_ACCESS_KEY"
      sys.exit(1)
    
    return True