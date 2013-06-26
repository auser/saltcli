import StringIO
from fabric.api import sudo, put, run
from fabric.tasks import execute
from saltcli.utils.ssh import Ssh
from saltcli.utils import utils
from saltcli.utils.utils import build_fabric_env
import os, sys, time
import importlib

class Provider(object):
  """Provider"""
  def __init__(self, config):
    super(Provider, self).__init__()
    config = self._build_provider_config(config)
    self.config = config
    self.ssh = Ssh(config)
    
  def launch(self, conf={}):
    pass
    
  def teardown(self, conf={}):
    pass
    
  def get(self, name):
    pass
    
  def all(self):
    pass
    
  def highstate(self, instance):
    name = instance.name
    if name == "master":
      cmd = "salt *"
    else:
      cmd = "salt-call"
    
    if instance:
      salt_dir = os.path.join(os.getcwd(), "deploy", "salt/")
      instance.environment.master_server().upload(salt_dir, "/srv/salt")
      
      def highstate():
        sudo("salt-call mine.update".format(cmd))
        sudo("salt-call state.highstate".format(cmd))
      
      env = build_fabric_env(instance)
      execute(highstate)
    else:
      print "There was an error finding the instance you're referring to by name: {0}".format(name)
    
  ## PRIVATE
  def bootstrap(self, instances):
    this_dir = os.path.dirname(os.path.realpath(__file__))
    bootstrap_dir = os.path.join(this_dir, "..", "..", "bootstrap")
    
    def get_script(instance):
      if instance.ismaster():
        script_name = "master.sh"
      else:
        script_name = "minion.sh"
      return os.path.join(bootstrap_dir, script_name)
        
    def _upload_and_run_bootstrap_script(instance):    
      ## Upload script
      if instance.ismaster():
        salt_dir = os.path.join(os.getcwd(), "deploy", "salt/")
        instance.upload(salt_dir, "/srv/salt")
        master_server_ip = "127.0.0.1"
      else:
        master_server_ip = self._master_server().ip_address
    
      ## Run bootstrap script
      local_file = get_script(instance)
      print "Uploading {0}".format(local_file)
      instance.upload(local_file, "/tmp/")
      index = len(self.all()) + 1
      
      def bootstrap_script():
        # cmd = "sudo /bin/sh #{remotepath} #{provider.to_s} #{name} #{master_server.preferred_ip} #{environment} #{index} #{rs}"
        script_name = os.path.basename(get_script(instance))
        sudo("chmod u+x /tmp/{script}".format(script=script_name))
        sudo("/tmp/{script} {inst_name} {master_server} {env} {index} {rs}".format(
          script = script_name,
          provider_name = self.__class__.__name__.lower(),
          inst_name = instance.instance_name,
          master_server = master_server_ip,
          env = instance.environment.environment,
          index = index,
          rs = ",".join(instance.roles())
        ))
    
      ## Run bootstrap script
      execute(bootstrap_script)
      if instance.ismaster():
        # Don't generate a new saltmaster key
        self.accept_minion_key(instance)
        
    [_upload_and_run_bootstrap_script(inst) for inst in instances]
    
  ## Accept the minion key
  def accept_minion_key(self, instance):
    def accept_key():
      sudo("salt-key -a {0}".format(instance.instance_name))
    
    execute(accept_key)
    # priv, pub = utils.gen_keys()
    # 
    # def _create():
    #   pki_dir = "/etc/salt/pki/minion/"
    #   priv_key = os.path.join(pki_dir, "minion.pem")
    #   put(StringIO.StringIO(priv), priv_key, use_sudo=True, mode=0600)
    #   pub_key = os.path.join(pki_dir, "minion.pub")
    #   put(StringIO.StringIO(pub), pub_key, use_sudo=True, mode=0600)
    #   
    # def _accept(**kwargs):  
    #   pki_dir = "/etc/salt/pki/master"
    #   for key_dir in ('minions', 'minions_pre', 'minions_rejected'):
    #       key_path = os.path.join(pki_dir, key_dir)
    #       sudo("mkdir -p {0}".format(key_path))
    #       
    #   for key_dir in ('minions_pre', 'minions_rejected'):
    #     oldkey = os.path.join(pki_dir, key_dir, name)
    #     sudo("rm -f {0}".format(oldkey))
    #     
    #   key = os.path.join(pki_dir, 'minions', name)
    #   put(StringIO.StringIO(pub), key, use_sudo=True)
    #   sudo("chown root:root {0}".format(key))
    #   
    # self.ssh.execute(inst, _create)
    # self.ssh.execute(self._master_server(), _accept)
    
  def remove_minion_key(self, name):
    def _remove_minion_key():
      pki_dir = "/etc/salt/pki/master"
      key = os.path.join(pki_dir, 'minions', name)
      sudo("rm -f {0}".format(key))
      
    self.ssh.execute(self._master_server(), _remove_minion_key)
  
  def upload(self, inst, args):
    if len(args) == 0:
      working_dir = os.getcwd()
      args = [os.path.join(working_dir, "deploy", "salt/")]
    self.ssh.upload(inst, *args)
    
  def _master_server(self):
    for inst in self.all():
      if inst.tags['instance_name'] == "master":
        return inst
    return None
    
  def _build_provider_config(self, config):
    if config['keyname'][0] == "/":
      config['key_file'] = config['keyname']
    else:
      home = os.environ['HOME']
      config['key_file'] = os.path.join(home, ".ec2", config['keyname'])
    return config

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