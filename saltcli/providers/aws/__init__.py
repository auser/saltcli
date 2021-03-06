import os, sys, base64
import boto, boto.ec2
import time
from stat import *
import xml.etree.ElementTree as ET
from saltcli.utils.utils import get_colors
from saltcli.providers import Provider, dict_merge
from saltcli.models.instance import Instance
from saltcli.providers.aws.keypair import setup_keypair, key_name, key_filename
from saltcli.providers.aws.security_group import setup_security_group
from saltcli.providers.aws.block_mappings import block_mappings

class Aws(Provider):
  def __init__(self, environment, config):
    super(Aws, self).__init__(environment, config)
    self._load_conns()
    # Load the running instances
    self.in_launch_mode = False
    self.running_instances = None
    # self._load_connection()
    
  ## Public methods
  def launch(self, instances):
    if not isinstance(instances, dict):
      instances = [instances]
    launched_instances = {}
    to_launch_instances = instances
    self.in_launch_mode = True

    ## Launch an instance (local to this method)
    def _launch_instance(name, inst):
      launch_config = self._load_machine_desc(name)
      if inst.get():
        colors = get_colors()
        inst.environment.info("{0}Not launching {1}. It is already launched.{2[ENDC]}".format(colors['RED'], name, colors))
        instance = inst
      else:
        instance = self.launch_single_instance(inst)
        self.ssh.wait_for_ssh(instance.ip_address(), instance.ssh_port())
      return instance

    # We need to launch the master first
    if 'master' in to_launch_instances:
      instance = _launch_instance('master', to_launch_instances['master'])
      launched_instances['master'] = instance
      del to_launch_instances['master']

    for name, inst in to_launch_instances.iteritems():
      instance = _launch_instance(name, inst)
      launched_instances[name] = instance

    self.in_launch_mode = False
    return launched_instances

  def launch_and_bootstrap(self, instances):
    launched_instances = self.launch(instances)
    self.bootstrap(launched_instances)
    
  ## Launch a single instance
  ## This will take the configuration
  def launch_single_instance(self, instance):
    launch_config = self._load_machine_desc(instance.name)
    ## RELOAD the ec2 connection based on a new region
    if 'region' in launch_config:
      conn = self._load_connection_for_region(launch_config['region'])
    elif self.config['region'] != self.conn.region:
      conn = self._load_connection_for_region(self.config['region'])
    
    keypair         = setup_keypair(conn, instance, self.config)
    all_roles       = self._load_all_roles()
    security_group  = setup_security_group(conn, instance, self, launch_config, all_roles)
    colors          = get_colors()
    
    print """Launching an AWS instance:
    Image:              {color}{image_id}{colors[ENDC]}
    Keyname:            {color}{key_name}{colors[ENDC]}
    security_group:     {color}{security_group}{colors[ENDC]}
    flavor:             {color}{flavor}{colors[ENDC]}
    placement:          {color}{placement}{colors[ENDC]}
    availability_zone:  {color}{availability_zone}{colors[ENDC]}
    """.format(
      image_id=launch_config['image_id'],
      key_name=keypair,
      security_group=security_group.name,
      flavor=launch_config['flavor'],
      placement=conn.region,
      availability_zone=launch_config['availability_zone'],
      color=colors['YELLOW'],
      colors=colors
    )

    launch_opts = {
      'key_name': keypair,
      'security_groups': [security_group.name],
      'instance_type': launch_config['flavor'],
      'block_device_map': block_mappings(launch_config['flavor']),
      'placement': launch_config['availability_zone'],
    }

    if 'user_data' in launch_config:
      user_data = launch_config['user_data']
      if os.path.isfile(user_data):
        launch_opts['user_data'] = open(user_data).read()
      else:
        launch_opts['user_data'] = user_data

    try:
      reservation = conn.run_instances(launch_config['image_id'], 
          **launch_opts)
    except boto.exception.EC2ResponseError as e:
      print "Exception: {0}".format(e)
      if e.status == 400:
        sys.exit(-1)
    instance.environment.debug("{0}Launching...{1[ENDC]}".format(colors['GREEN'], colors))
    running_instance = reservation.instances[0] #### <~ ew
    # Check up on its status every so often
    instance.environment.debug("{0}Launched. Waiting for the instance to become available.{1[ENDC]}".format(colors['YELLOW'], colors))
    try:
      status = running_instance.update()
    except:
      True
    while status == 'pending' or running_instance.ip_address is None:
        time.sleep(10)
        status = running_instance.update()
    instance.environment.info("Instance {0} launched at {1}".format(running_instance.id, running_instance.ip_address))
    
    if status == 'running':
      instance.environment.debug("""
Adding tags:
  name: {color}{name}{endcolor}
  instance_name: {color}{instance_name}{endcolor}
  environment: {color}{environment}{endcolor}
      """.format( name=instance.name, 
                  instance_name=instance.instance_name, 
                  environment=instance.environment.environment,
                  color=colors['YELLOW'],
                  endcolor=colors['ENDC']))

      conn.create_tags([running_instance.id], {
        'name': instance.name,
        'Name': instance.instance_name,
        'instance_name': instance.instance_name,
        'environment': instance.environment.environment
        })
    else:
      print "Instance status: {0}".format(status)

    ## Update this into environment.py
    instance = Instance(instance.name, instance.instance_options, instance.environment)
    instance.environment.instances[instance.name] = instance
    
    return instance
      
  
  def teardown(self, instance):
    """Teardown"""
    colors = get_colors()
    if instance:
      instance.environment.debug("{0}Tearing down instance: {1}{2[ENDC]}".format(
        colors['GREEN'], instance.instance_name, colors))
      conn = self._load_connection_for_instance(instance)
      conn.terminate_instances([instance.get().id])
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
      return None
      
  def _get_by_name(self, name):
    for inst in self.all():
      if name == inst['instance'].tags.get('instance_name', None) or name == inst['instance'].tags.get('name', None):
        return inst
    return None
    
  ## Get the list of running instances for this cluster
  ## this is raw data, not instance objects
  def all(self):
    """List instances"""
    if self.running_instances is None or self.in_launch_mode:
      running_instances = []
      for name, c in self._conns.items():
        reservations = c.get_all_instances()
        for res in reservations:
          for inst in res.instances:
            if inst.key_name == key_name(c, self.config) and inst.update() == 'running':
              if not inst.tags:
                unknownId = 'Unknown' + str(len(running_instances))
                running_instances.append({
                    'instance': inst,
                    'instance_obj': Instance(unknownId, {}, self.environment),
                    'ip': inst.ip_address,
                    'name': unknownId,
                    'region_name': name,
                    'conn': c,
                    'tags': {}
                  })
              else:
                inst_d = {
                  'name': inst.tags['name'],
                  'instance': inst,
                  'instance_obj': Instance(inst.tags['name'], {}, self.environment),
                  'ip': inst.ip_address,
                  'region_name': name,
                  'conn': c,
                  'tags': inst.tags
                }
                running_instances.append(inst_d)
      self.running_instances = running_instances
    return self.running_instances
    
  ## All the names of every instance
  def all_running_names(self):
    running_instance_names = []
    for i in self.all():
      if 'name' in i['instance'].tags:
        running_instance_names.append(i['instance'].tags['name'])
    return running_instance_names
    
    
  ## Create the security group and attach the appropriate permissions
  #   ## Now that we have our connection...
  #   group_name = key_name(conn, instance, self.config) + "-" + instance.instance_name
  #   groups = [g for g in conn.get_all_security_groups() if g.name == group_name]
  #   group = groups[0] if groups else None
  #   if not group:
  #     instance.environment.debug("Creating group '%s'..."%(group_name,))
  #     group = conn.create_security_group(group_name, "A group for %s"%(group_name,))
    
  #   expected_rules = []
  #   if 'ports' in launch_config:
  #     for proto, port_conf in launch_config['ports'].iteritems():
  #       for cidr, ports in port_conf.iteritems():
  #         for port in ports:
  #           rule = SecurityGroupRule(str(proto), str(port), str(port), str(cidr), None)
  #           expected_rules.append(rule)
    
  #   # for g in self.conn.get_all_security_groups():
  #     # expected_rules.append(SecurityGroupRule('tcp', 22, 65535, '0.0.0.0/0', g.name))
    
  #   colors = get_colors()
  #   if self.environment.opts.get('answer_yes', False):
  #     self.environment.info('''{0}Updating security group to match the configuration for group {2}{1[ENDC]}'''.format(colors['RED'], colors, group_name))
  #     current_rules = []
  #     for rule in group.rules:
  #       if not rule.grants[0].cidr_ip:
  #         current_rule = SecurityGroupRule(str(rule.ip_protocol),
  #                           str(rule.from_port),
  #                           str(rule.to_port),
  #                           "0.0.0.0/0",
  #                           str(rule.grants[0].name))
  #       else:
  #         current_rule = SecurityGroupRule(str(rule.ip_protocol),
  #                           str(rule.from_port),
  #                           str(rule.to_port),
  #                           str(rule.grants[0].cidr_ip),
  #                           None)
                            
  #       if current_rule not in expected_rules:
  #         self._revoke(group, conn, current_rule)
  #       else:
  #         current_rules.append(current_rule)
            
  #     for rule in expected_rules:
  #       if rule not in current_rules:
  #         self._authorize(group, conn, rule)
  #   else:
  #     self.environment.info('''{0}
  #       Not updating the security group authorizations for the group:
  #       {2}
  #       If you want to update the security group rules, pass `-y` option{1[ENDC]}
  #       '''.format(colors['BLUE'], colors, group_name))
    
  #   return group
  
  # def _modify_sg(self, conn, group, rule, authorize=False, revoke=False):
  #     src_group = None
  #     if rule.src_group_name:
  #         src_group = conn.get_all_security_groups([rule.src_group_name,])[0]
 
  #     if authorize and not revoke:
  #         print "Authorizing missing rule %s..."%(rule,)
  #         group.authorize(ip_protocol=rule.ip_protocol,
  #                         from_port=str(rule.from_port),
  #                         to_port=str(rule.to_port),
  #                         cidr_ip=rule.cidr_ip,
  #                         src_group=src_group)
  #     elif not authorize and revoke:
  #         print "Revoking unexpected rule %s..."%(rule,)
  #         group.revoke(ip_protocol=rule.ip_protocol,
  #                      from_port=str(rule.from_port),
  #                      to_port=str(rule.to_port),
  #                      cidr_ip=rule.cidr_ip,
  #                      src_group=src_group)
 
 
  # def _authorize(self, group, conn, rule):
  #     """Authorize `rule` on `group`."""
  #     return self._modify_sg(conn, group, rule, authorize=True)
 
 
  # def _revoke(self, group, conn, rule):
  #     """Revoke `rule` on `group`."""
  #     return self._modify_sg(conn, group, rule, revoke=True)
  
  # Convenience method to get the keypair
  # TODO: Move this into the parent class
  # def key_name(self, conn):
  #   if isinstance(conn, Instance):
  #     conn = self._load_connection_for_instance(conn)
  #   if conn is None:
  #     conn = self.conn
  #   return "{0}-{1}".format(conn.region.name, self.config['keyname'])
    
  def key_filename(self, instance):
    conn = self._load_connection_for_instance(instance)
    return key_filename(conn, instance, self.config)
    
  ## Load conn for instance
  def _load_connection_for_instance(self, instance):
    for inst_d in self.all():
      if inst_d['tags'] and 'name' in inst_d['tags'] and inst_d['tags']['name'] == instance.name:
        return inst_d['conn']
    return None
  
  ## Setup connection
  def _load_connection(self, **kwargs):
    """Load connection"""
    self._load_credentials()
    new_kwargs = kwargs.copy()
    if 'region' in kwargs:
      new_kwargs['region'] = boto.ec2.get_region(kwargs['region'])
    else:
      new_kwargs['region'] = boto.ec2.get_region(self.config['region'])
    
    self.conn = boto.connect_ec2(self.access_key, self.secret_key, **new_kwargs)
    return self.conn
    
  ## Setup connections
  def _load_connection_for_region(self, region_name, **kwargs):
    if not region_name in self._conns:
      self._conns[region_name] = self._load_connection(region=region_name)
    
    return self._conns[region_name]
    
  ## Load all the connections we know about
  def _load_conns(self):
    regions = []
    
    def _recursive_load_region(dictionary={}):
      for k, v in dictionary.items():
        if isinstance(v, dict):
          _recursive_load_region(v)
        else:
          if k == "region" and v not in regions:
            regions.append(v)
            self._load_connection_for_region(v)
        
    for dictionary in [self.config['machines'], self.config]:
      _recursive_load_region(dictionary)
    
    return regions
    
  def _load_machine_desc(self, name):
    """Load machine descriptions"""
    machines = self.config['machines']
    default_aws_config = {
      'region': 'us-east-1',
      'availability_zone': 'us-east-1b',
    }
    default = dict_merge(machines['default'], default_aws_config)
    try:
      machine_config = dict_merge(machines[name], default)
    except Exception, e:
      machine_config = default
    
    return machine_config

  def _load_all_roles(self):
    machine_config = self.environment.config['machines']
    all_known_roles = []
    for name, d in machine_config.iteritems():
      if 'roles' in d:
        for role in d['roles']:
          if role not in all_known_roles:
            all_known_roles.append(role)

    return all_known_roles
    
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
        self.secret_key = os.environ['AWS_SECRET_KEY']
    except KeyError: 
      print "Please set the environment variable AWS_SECRET_KEY"
      sys.exit(1)
    
    return True
