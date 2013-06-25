from fabric.api import sudo
from fabric.tasks import execute
from saltcli.lib.ssh import Ssh
import os

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
    
  def list_instances(self):
    pass
    
  def highstate(self, conf={}):
    name = conf.get('original_name', "master")
    if name == "master":
      cmd = "salt *"
      inst = self._master_server()
    else:
      cmd = "salt-call"
      inst = self.get(name)
      
    hosts = [inst.ip_address]
    
    self.ssh.sudo_command(inst, "{0} state.highstate".format(cmd))
    
  ## PRIVATE
  def bootstrap(self, inst, conf={}):
    # local_file
    this_dir = os.path.dirname(os.path.realpath(__file__))
    c = conf.get('bootstrap', {
      'master': os.path.join(this_dir, "..", "..", "bootstrap", "master.sh"),
      'minion': os.path.join(this_dir, "..", "..", "bootstrap", "minion.sh"),
    })
    if conf.get('original_name', 'master') == "master":
      script_name = "master.sh"
      local_file = c['master']
    else:
      script_name = "minion.sh"
      local_file = c['minion']
      
    self.upload(inst, [])
    self.ssh.upload(inst, local_file, "/srv/salt/")
    
    def bootstrap_script():
      # cmd = "sudo /bin/sh #{remotepath} #{provider.to_s} #{name} #{master_server.preferred_ip} #{environment} #{index} #{rs}"
      sudo("/srv/salt/{script} {provider_name} {inst_name} {master_server} {env} {index} {rs}".format(
        script = script_name,
        provider_name = self.__class__.__name__.lower(),
        inst_name = conf['original_name'],
        master_server = self._master_server().ip_address,
        env = conf['environment'],
        index = 1,
        rs = "master"
      ))
    
    execute(bootstrap_script, hosts=[inst.ip_address])
    
  def upload(self, inst, args):
    if len(args) == 0:
      working_dir = os.getcwd()
      args = [os.path.join(working_dir, "deploy", "salt/")]
    self.ssh.upload(inst, *args)
    
  def _master_server(self):
    for inst in self.list_instances():
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