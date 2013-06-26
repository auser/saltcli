import StringIO
from fabric.api import sudo, put
from fabric.tasks import execute
from saltcli.utils.ssh import Ssh
from saltcli.utils import utils
import os, sys, time
import importlib

class Provider(object):
  """Provider"""
  def __init__(self, config):
    super(Provider, self).__init__()
    config = self._build_config(config)
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
    
  def highstate(self, conf={}):
    name = conf.get('original_name', "master")
    if name == "master":
      cmd = "salt *"
      inst = self._master_server()
    else:
      cmd = "salt-call"
      inst = self.get(name)
    
    if inst:
      hosts = [inst.ip_address]
    
      self.ssh.sudo_command(inst, "{0} mine.update".format(cmd))
      self.ssh.sudo_command(inst, "{0} state.highstate".format(cmd))
    else:
      print "There was an error finding the instance you're referring to by name: {0}".format(name)
    
  ## PRIVATE
  def bootstrap(self, inst, conf={}):
    name = conf['name']
    # local_file
    this_dir = os.path.dirname(os.path.realpath(__file__))
    c = conf.get('bootstrap', {
      'master': os.path.join(this_dir, "..", "..", "bootstrap", "master.sh"),
      'minion': os.path.join(this_dir, "..", "..", "bootstrap", "minion.sh"),
    })
    ## Upload script
    if conf.get('original_name', 'master') == "master":
      script_name = "master.sh"
      local_file = c['master']
      self.upload(self._master_server(), [])
    else:
      script_name = "minion.sh"
      local_file = c['minion']
    
    ## Run bootstrap script
    print "Uploading {0}".format(local_file)
    self.ssh.upload(inst, local_file, "/srv/salt/")
    index = len(self.all()) + 1
    
    def bootstrap_script():
      # cmd = "sudo /bin/sh #{remotepath} #{provider.to_s} #{name} #{master_server.preferred_ip} #{environment} #{index} #{rs}"
      sudo("chmod u+x /srv/salt/{script}".format(script=script_name))
      sudo("/srv/salt/{script} {inst_name} {master_server} {env} {index} {rs}".format(
        script = script_name,
        provider_name = self.__class__.__name__.lower(),
        inst_name = name,
        master_server = self._master_server().ip_address,
        env = conf['environment'],
        index = index,
        rs = ",".join(conf.get('roles', []))
      ))
    
    ## Run bootstrap script
    execute(bootstrap_script, hosts=[inst.ip_address])
    
    # Don't generate a new saltmaster key
    if conf.get('original_name', 'master') != 'master':
      self.accept_minion_key(inst, name)
  
  ## Accept the minion key
  def accept_minion_key(self, inst, name):
    priv, pub = utils.gen_keys()
    
    def _create():
      pki_dir = "/etc/salt/pki/minion/"
      priv_key = os.path.join(pki_dir, "minion.pem")
      put(StringIO.StringIO(priv), priv_key, use_sudo=True, mode=0600)
      pub_key = os.path.join(pki_dir, "minion.pub")
      put(StringIO.StringIO(pub), pub_key, use_sudo=True, mode=0600)
      
    def _accept(**kwargs):  
      pki_dir = "/etc/salt/pki/master"
      for key_dir in ('minions', 'minions_pre', 'minions_rejected'):
          key_path = os.path.join(pki_dir, key_dir)
          sudo("mkdir -p {0}".format(key_path))
          
      for key_dir in ('minions_pre', 'minions_rejected'):
        oldkey = os.path.join(pki_dir, key_dir, name)
        sudo("rm -f {0}".format(oldkey))
        
      key = os.path.join(pki_dir, 'minions', name)
      put(StringIO.StringIO(pub), key, use_sudo=True)
      sudo("chown root:root {0}".format(key))
      
    
    self.ssh.execute(inst, _create)
    self.ssh.execute(self._master_server(), _accept)
    
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
  
  # Wait for ready
  def wait_for_ready(self, instance):
    self.ssh.wait_for_ssh(instance.ip_address())
    
  def _master_server(self):
    for inst in self.all():
      if inst.tags['original_name'] == "master":
        return inst
    return None
    
  def _build_config(self, config):
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