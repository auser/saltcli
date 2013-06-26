import sys
from saltcli.commands import Command

class Launch(Command):
  """docstring for Launch"""
  def __init__(self, env):
    super(Launch, self).__init__(env)
    
  def run(self):
    """Launch"""
    self.provider.launch(self.environment.instances)
    self.provider.bootstrap(self.environment.instances)
    