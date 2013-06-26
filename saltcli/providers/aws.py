import os, sys, base64
import boto
import time
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
    security_group = self._setup_security_group(instance, launch_config)
    
    reservation = self.conn.run_instances(launch_config['image_id'], 
                            key_name=instance.keyname(),
                            security_groups=[security_group.name],
                            instance_type=launch_config['flavor'],
                            )
    colors = get_colors()
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
        if inst.update() == 'running':
          running_instances.append(inst)
    return running_instances
    
  def all_names(self):
    running_instance_names = []
    for i in self.all():
      running_instance_names.append(i.tags['name'])
    return running_instance_names
    
  def _get_user_data(self, name):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    script_name = "master" if name == "master" else "minion"
    f = open(os.path.join(this_dir, '..', '..', 'bootstrap', script_name + '.sh'))
    return base64.b64encode(f.read())
    
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
  
  
  def _load_connection(self):
    """Load connection"""
    self._load_credentials()
    self.conn = boto.connect_ec2(self.access_key, self.secret_key)
    
  def _load_machine_desc(self, name):
    """Load machine descriptions"""
    machines = self.config['machines']
    default = machines['default']
    try:
      machine_config = dict_merge(machines[name], default)
    except Exception, e:
      print "ECEPTION: {0}".format(e)
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