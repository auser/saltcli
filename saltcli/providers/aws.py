import os, sys, base64
import boto
import time
from saltcli.providers import Provider, dict_merge
import collections

SecurityGroupRule = collections.namedtuple("SecurityGroupRule", ["ip_protocol", "from_port", "to_port", "cidr_ip", "src_group_name"])

class Aws(Provider):
  def __init__(self, config):
    super(Aws, self).__init__(config)
    self._load_connection()
    
  ## Public methods
  def launch(self, conf={}):
    """Launch"""
    launch_config = self._load_machine_desc(conf['original_name'])
    user_data = self._get_user_data(conf['original_name'])
    security_group = self._setup_security_group(conf, launch_config)
    reservation = self.conn.run_instances(launch_config['image_id'], 
                            key_name=self.config['keyname'],
                            security_groups=[security_group.name],
                            instance_type=launch_config['flavor'],
                            )
    sys.stdout.write("Launching...")
    instance = reservation.instances[0] #### <~ ew
    # Check up on its status every so often
    status = instance.update()
    while status == 'pending':
        time.sleep(5)
        sys.stdout.write('.')
        sys.stdout.flush()
        status = instance.update()
    print "Instance {0} launched at {1}".format(instance.id, instance.ip_address)
    if status == 'running':
      instance.add_tag("name", conf['name'])
      instance.add_tag('original_name', conf['original_name'])
      instance.add_tag('environment', conf['environment'])
    else:
      print "Instance status: {0}".format(status)
      
    salt_dir = os.path.join(os.getcwd(), "deploy", "salt")
    retry = True
    while retry:
      try:
        self.ssh.run_command(instance, "echo 'trying to connect...'", conf)
        retry = False
      except:
        time.sleep(10)
    self.ssh.upload(instance, salt_dir, "/srv/salt", conf)
    
    return instance
      
  def teardown(self, name):
    """Teardown"""
    inst = self.get(name)
    if inst:
      print "Tearing down instance: {0}".format(name)
      self.conn.terminate_instances([inst.id])
    else:
      print "Could not find instance by name {0}".format(name)
      
  def get(self, name):
    if isinstance(name, str):
      return self._get_by_name(name)
    elif isinstance(name, boto.ec2.instance.Instance):
      return name
    else:
      print name
      
  def _get_by_name(self, name):
    for inst in self.list_instances():
      if name == inst.tags.get('name', None):
        return inst
    return None
    
  def list_instances(self):
    """List instances"""
    running_instances = []
    reservations = self.conn.get_all_instances()
    for res in reservations:
      for inst in res.instances:
        if inst.update() == 'running':
          running_instances.append(inst)
    return running_instances
    
  def _get_user_data(self, name):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    script_name = "master" if name == "master" else "minion"
    f = open(os.path.join(this_dir, '..', '..', 'bootstrap', script_name + '.sh'))
    return base64.b64encode(f.read())
    
  def _setup_security_group(self, config, launch_config):
    group_name = self.config['keyname'] + "-" + config['name']
    groups = [g for g in self.conn.get_all_security_groups() if g.name == group_name]
    group = groups[0] if groups else None
    if not group:
      print "Creating group '%s'..."%(group_name,)
      group = self.conn.create_security_group(group_name, "A group for %s"%(group_name,))
    
    expected_rules = []
    if 'ports' in launch_config:
      for proto, port_conf in launch_config['ports'].iteritems():
        for cidr, ports in port_conf.iteritems():
          for port in ports:
            rule = SecurityGroupRule(str(proto), str(port), str(port), str(cidr), None)
            expected_rules.append(rule)
    
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
      machine_config = default
    
    return machine_config
    
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