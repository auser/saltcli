import importlib
import sys

class Command(object):
  """Command"""
  def __init__(self, environment):
    super(Command, self).__init__()
    self.environment  = environment
    self.provider     = environment.provider
    self.run()
    
  def load_provider(self):
    """docstring for load_provider"""
    provider_config = self.config['providers'][self.provider_name]
    return get_provider(self.provider_name)(self.environment, provider_config)