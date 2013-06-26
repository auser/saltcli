import sys
from saltcli.commands import Command

class Launch(Command):
  """docstring for Launch"""
  def __init__(self, env):
    super(Launch, self).__init__(env)
    
  def run(self):
    """Launch"""
    # if self.environment.get('plan'):
    #   for plan, pack in self.config_obj.plans().iteritems():
    #     for c in pack:
    #       for name, opts in c.items():
    #         conf = self.obj.copy()
    #         if opts['roles']:
    #           conf['roles'] = opts['roles']
    #         conf['instance_name'] = name
    #         conf['name'] = conf['environment'] + "-" + name
    #         self.launch_and_bootstrap(conf['name'], conf)
    self.launch_and_bootstrap()
    # self.provider.highstate(self.obj)
      
  def launch_and_bootstrap(self):
    self.provider.launch(self.environment.instances)
    self.provider.bootstrap(self.environment.instances)
