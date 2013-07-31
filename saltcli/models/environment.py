import sys, os
import yaml
import logging
import importlib

from saltcli.utils.utils import get_colors
from saltcli.utils.ssh import Ssh
from saltcli.models.instance import Instance

class Environment(object):
  def __init__(self, opts):
    super(Environment, self).__init__()
    self.opts           = opts
    self._load_config_file(opts['config_file'])
    self.provider_name  = opts['provider']
    # TODO: Make this dynamic so different configuration
    # file formats are acceptable
    self.load_conf()
    self.setup_logging()
    self.load_provider()
    ## Setup naming
    self.environment  = opts['environment']
    self.ssh = self.provider.ssh
    self.orig_opts = opts
    
    ## PLANS
    self.plan = None
    plan_name = opts.get('plan')
    if plan_name:
      if plan_name in self.config.get('plans', []):
        self.plan = self.config['plans'][plan_name]
        
    self.instances    = {}
    if opts.get('all', False):
      if not self.plan is None: 
        all_instance_names = self.plan.keys()
      else:
        all_instance_names = self.provider.all_names()
    else:
      all_instance_names = opts['name']
    for inst_name in all_instance_names:
      if not self.plan is None: 
        instance_options = self.plan.get(inst_name)
      else:
        instance_options = {
          'roles': opts['roles']
        }
      if instance_options is None:
        self.error("No options found for the instance named: {0}\nPlease check your configuration and try again".format(inst_name))
      inst = Instance(inst_name, instance_options, self)
      self.instances[inst_name] = inst
  
  ## Get config
  def get(self, key, default=None):
    self.config.get(key, default)
    
  ## Get the master server
  def master_server(self):
    for name in self.provider.all_names():
      if name == "master":
        return Instance(name, {}, self)
    return None
  
  ## Load providers
  def load_provider(self):
    provider_config = self.config.get('providers')[self.provider_name]
    mod = importlib.import_module("saltcli.providers." + self.provider_name)
    self.provider =  getattr(mod, self.provider_name.capitalize())(self, provider_config)
  
  ## Load the config file
  def load_conf(self):
    stream = open(self.config_file)
    self.config = yaml.load(stream)
    
  ## Debug message
  def setup_logging(self):
    self.log = logging.getLogger(__name__)
    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    
    colors = get_colors()
    hcolor = colors['GREEN']
    # create formatter
    formatter = logging.Formatter('%(asctime)s [{0}%(levelname)s{1[ENDC]}]: %(message)s'.format(
      hcolor, colors
    ))

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    self.log.addHandler(ch)
    
  def debug(self, msg): self.log.debug(msg)
  def info(self, msg): self.log.info(msg)
  def error(self, msg):
    colors = get_colors()
    msg = "{0}{1}{2[ENDC]}".format(colors['RED'], msg, colors)
    self.log.error(msg)
    sys.exit(-1)
    
  def _load_config_file(self, config_file):
    try:
      if os.path.isfile(config_file):
        self.config_file = config_file
      elif os.path.isfile(os.environ['SALT_CONFIG_FILE']):
        self.config_file = os.environ['SALT_CONFIG_FILE']
    except Exception, e:
      print "Please either pass a config file with -c [file] or set as an environment variable as SALT_CONFIG_FILE"
      sys.exit(1)