import importlib
import sys

class Command(object):
  """Command"""
  def __init__(self, provider_name, args, conf, obj):
    super(Command, self).__init__()
    self.args = args
    self.config = conf.yaml()
    self.config_obj = conf
    self.obj = obj
    
    self.provider_name = provider_name
    self.provider = self.load_provider()
    self.run()
    
  def load_provider(self):
    """docstring for load_provider"""
    provider_config = self.config['providers'][self.provider_name]
    print "provider_name: {0}".format(provider_config)
    return get_provider(self.provider_name)(provider_config)

def get_method(str):
  mod = importlib.import_module("saltcli.commands." + str)
  return getattr(mod, str.capitalize())

def get_provider(str):
  mod = importlib.import_module("saltcli.providers." + str)
  return getattr(mod, str.capitalize())