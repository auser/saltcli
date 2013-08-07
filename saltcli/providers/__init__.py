import StringIO
from fabric.api import sudo, put, run, settings, parallel
from fabric.tasks import execute
from saltcli.utils.ssh import Ssh
from saltcli.utils import utils
from saltcli.utils.utils import build_fabric_env
from saltcli.utils.utils import get_colors
import saltcli.utils.template
import os, sys, time, tempfile
import yaml
from stat import *
import importlib

class Provider(object):
  """Provider"""
  def __init__(self, environment, config):
    super(Provider, self).__init__()
    self.environment = environment
    config = self._build_provider_config(config)
    self.config = config
    self.ssh = Ssh(config)
    self._conns = {}
    
  def launch(self, conf={}):
    pass
    
  def teardown(self, conf={}):
    pass
    
  def get(self, name):
    pass
    
  def all(self):
    pass
    
  @parallel
  def _prepare_for_highstate(self):
    try:
      with settings(warn_only=True):
        sudo("salt-call saltutil.sync_all")
        sudo("salt-call mine.update")
    except Exception, e: 
      print "There was an error preparing for highstate: {0}".format(e)
    
  def highstate(self, instances):
    if instances:
      instances = instances.values()
      salt_dir = os.path.join(os.getcwd(), "deploy", "salt/")
      instances[0].environment.master_server().upload(salt_dir, "/srv/salt")
      
      @parallel
      def highstate():
        with settings(warn_only=True):
          sudo("salt-call state.highstate")

      def highstate_master():
        with settings(warn_only=True):
          sudo("salt \* state.highstate")

      env = build_fabric_env(instances)
      execute(self._prepare_for_highstate)
      if self.environment.opts['all'] is False:
        execute(highstate)
      else:
        env = build_fabric_env(self.environment.master_server())
        execute(highstate_master)

    else:
      print "There was an error finding the instance you're referring to by name: {0}".format(name)
      
  def overstate(self, instances):
    colors = get_colors()
    if instances:
      instances = instances.values()
      salt_dir = os.path.join(os.getcwd(), "deploy", "salt/")
      instances[0].environment.master_server().upload(salt_dir, "/srv/salt")
      
      env = build_fabric_env(self.environment.master_server())
      execute(self._prepare_for_highstate)
      def highstate():
        sudo("salt-run state.over")
      
      execute(highstate)
    else:
      self.environment.debug("There was an error finding any instances")
  
  ## Run a command
  def cmdrun(self, command):
    if self.environment.opts['all'] is False:
      names = self.environment.instances.keys()
      instance_names = ["*{0}*".format(name) for name in names]
    else:
      instance_names = ['*']
    @parallel
    def _cmdrun():
      sudo("salt -C '{0}' cmd.run {1}".format(" or ".join(instance_names), command))
    
    env = build_fabric_env(self.environment.master_server())
    execute(_cmdrun)
    
  ## PRIVATE
  def bootstrap(self, instances):        
    def _upload_and_run_bootstrap_script(instance):    
      ## Upload script
      if instance.ismaster():
        salt_dir = os.path.join(os.getcwd(), "deploy", "salt/")
        instance.upload(salt_dir, "/srv/salt")
        master_server_ip = "127.0.0.1"
      else:
        master_server_ip = instance.environment.master_server().private_ip_address()
      
      ## Generate new keys for this minion
      priv, pub = utils.gen_keys()
      index = len(self.all()) + 1

      ## Run bootstrap script
      local_file = saltcli.utils.template.gen_rendered_script(instance, {
        'hostname': instance.instance_name,
        'saltmaster': master_server_ip,
        'environment': instance.environment.environment,
        'index': index,
        'roles': instance.roles,
        'priv_key': priv,
        'pub_key': pub,
        })

      print "Uploading {0} to {1}".format(local_file.name, instance.name)
      instance.upload(local_file.name, "/tmp")
      
      def bootstrap_script():
        # cmd = "sudo /bin/sh #{remotepath} #{provider.to_s} #{name} #{master_server.preferred_ip} #{environment} #{index} #{rs}"
        script_name = os.path.basename(local_file.name)
        sudo("chmod u+x /tmp/{script_name}".format(script_name=script_name))
        
        instance.environment.debug("Running bootstrap_script: {0}".format(script_name))
        sudo("/tmp/{0}".format(script_name))
        sudo("restart salt-minion || start salt-minion || true")
    
      ## Cleanup
      local_file.close()
      ## Run bootstrap script
      execute(bootstrap_script)
      # if not instance.ismaster():
      self.accept_minion_key(instance, pub, False)
        
    if 'master' in instances:
      _upload_and_run_bootstrap_script(instances['master'])
      del instances['master']
      
    [_upload_and_run_bootstrap_script(inst) for name, inst in instances.iteritems() if inst != None]
    
  ## SaltAuth
  def salt_auth(self, instances):
    def one_pass():
      with settings(warn_only=True):
        sudo("salt-call grains.item roles")

    def handle_salt_auth(instance):
      priv, pub = utils.gen_keys()
      master_server_ip = instance.environment.master_server().private_ip_address()
      self.remove_minion_key(instance, pub, True)
      self.accept_minion_key(instance, pub, False)

      env = build_fabric_env(instance)
      execute(one_pass)
    [handle_salt_auth(inst) for name, inst in instances.iteritems() if inst != None]

  ## Accept the minion key
  def accept_minion_key(self, instance, pub, recreate_key=False):
    ## Create a new  minion key on the minion    
    if recreate_key:
      def _create():
        pki_dir = "/etc/salt/pki/minion/"
        priv_key = os.path.join(pki_dir, "minion.pem")
        put(StringIO.StringIO(priv), priv_key, use_sudo=True, mode=0600)
        pub_key = os.path.join(pki_dir, "minion.pub")
        put(StringIO.StringIO(pub), pub_key, use_sudo=True, mode=0600)
        sudo("restart salt-minion || start salt-minion || true")

      env = build_fabric_env(instance)
      self.ssh.execute(instance, _create, hosts=[instance.ip_address()])
      
    def _accept(**kwargs):  
      pki_dir = "/etc/salt/pki/master"
      if instance.ismaster():
        instance_name = "saltmaster"
      else:
        instance_name = instance.instance_name
        
      for key_dir in ('minions', 'minions_pre', 'minions_rejected'):
          key_path = os.path.join(pki_dir, key_dir)
          sudo("mkdir -p {0}".format(key_path))

      oldkey = os.path.join(pki_dir, 'minions_pre', instance_name)
      if os.path.isfile(oldkey):
        with open(oldkey) as fp:
          if fp.read() == pub:
            os.remove(oldkey)

      key = os.path.join(pki_dir, 'minions', instance_name)
      put(StringIO.StringIO(pub), key, use_sudo=True)
      sudo("chown root:root {0}".format(key))
      # sudo("restart salt-master || start salt-master || true")

    env = build_fabric_env(instance.environment.master_server())
    self.ssh.execute(instance.environment.master_server(), _accept, hosts=[instance.environment.master_server().ip_address()])
    
  # Set resetting true if we are resetting the node's keys
  def remove_minion_key(self, instance, resetting=False):
    if instance.environment.master_server():
      def _remove_minion_key():
        sudo("rm -f {0}".format("/etc/salt/pki/minion/minion.pem"))
        sudo("rm -f {0}".format("/etc/salt/pki/minion/minion.pub"))
        sudo("restart salt-minion || start salt-minion || true")

      def _remove_master_minion_key():
        pki_dir = "/etc/salt/pki/master"
        key = os.path.join(pki_dir, 'minions', instance.instance_name)
        sudo("rm -f {0}".format(key))
    
      if resetting:
        env = build_fabric_env(instance)
        execute(_remove_minion_key)
      env = build_fabric_env(instance.environment.master_server())
      execute(_remove_master_minion_key)
  
  def upload(self, inst, args):
    if len(args) == 0:
      working_dir = os.getcwd()
      args = [os.path.join(working_dir, "deploy", "salt/")]
    self.ssh.upload(inst, *args)


  ## Select the master machine for this cluster
  def _master_server(self):
    for inst in self.all():
      if inst.tags['instance_name'] == "master":
        return inst
    return None

  def get_instance_roles(self, instance_name):
    inst_d = self.get(str(instance_name))
    if inst_d is not None:
      roles = self.ssh.run_command(inst_d['instance_obj'], "sudo salt-call -l quiet grains.item roles")
      try:
        doc = yaml.load(roles)
        inst_d['roles'] = doc['roles']
        return doc
      except Exception, e:
        print "Exception: {0}".format(e)

  def set_instance_roles(self, instance, roles):
    inst_d = self.get(instance)

    yaml_conf = yaml.dump({'roles': roles})
    fi, path = tempfile.mkstemp('saltcli_')
    f = os.fdopen(fi, "w")
    f.write(yaml_conf)
    f.close()
    inst_d['instance_obj'].upload_file(path, '/etc/salt/grains')
    os.close(fi)
    if inst_d is not None:
      roles = self.ssh.run_command(inst_d['instance_obj'], "sudo restart salt-minion")

  ## Build a profile config
  def _build_provider_config(self, config):
    if not 'region' in config:
      config['region'] = 'us-east-1'
    
    if not 'availability_zone' in config:
      config['availability_zone'] = 'us-east-1'
    
    if config['keyname'][0] == "/":
      config['key_file'] = config['keyname']
    else:
      if 'key_dir' in config:
        key_dir = config['key_dir']
      else:
        key_dir = os.path.join(os.environ['HOME'], ".ec2")
      config['key_dir'] = key_dir
      config['key_file'] = os.path.join(key_dir, "{0}-{1}.pem".format(config['region'], config['keyname']))
      
    return config
    
  ## Local the machine config based on the config file
  def _load_machine_desc(self, name):
    """Load machine descriptions"""
    machines = self.config['machines']
    default = machines['default']
    try:
      machine_config = dict_merge(machines[name], default)
    except Exception, e:
      print "EXCEPTION: {0}".format(e)
      machine_config = default
    
    return machine_config

def dict_merge(target, obj):
  if not isinstance(obj, dict):
    return obj
  for k, v in obj.iteritems():
    if k in target and isinstance(target[k], dict):
      dict_merge(target[k], v)
    elif isinstance(v, list):
      if not k in target:
        target[k] = v
      else:
        target[k] = list(set(target[k] + v))
    elif k in target:
      target[k]
    else:
      target[k] = obj[k]
  return target