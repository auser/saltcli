import yaml
import logging
import importlib

from saltcli.models.instance import Instance

class Environment(object):
  def __init__(self, opts):
    super(Environment, self).__init__()
    self.opts           = opts
    self.config_file    = opts['config_file']
    self.provider_name  = opts['provider']
    # TODO: Make this dynamic so different configuration
    # file formats are acceptable
    self.load_conf()
    self.setup_logging()
    self.load_provider()
    ## Setup naming
    self.environment  = opts['environment']
    
    self.instances    = []
    if opts.get('all', False):
      all_instance_names = self.provider.all()
    else:
      all_instance_names = opts['name']
    for inst_name in all_instance_names:
      inst = Instance(inst_name, self)
      self.instances.append(inst)
  
  ## Get config
  def get(self, key, default=None):
    print self.config
    self.config.get(key, default)
  
  ## Load providers
  def load_provider(self):
    provider_config = self.config.get('providers')[self.provider_name]
    mod = importlib.import_module("saltcli.providers." + self.provider_name)
    self.provider =  getattr(mod, self.provider_name.capitalize())(provider_config)
  
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
    
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    self.log.addHandler(ch)
    
  def debug(self, msg): self.log.debug(msg)
  def info(self, msg): self.log.info(msg)
    