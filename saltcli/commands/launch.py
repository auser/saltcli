from saltcli.commands import Command

class Launch(Command):
  """docstring for Launch"""
  def __init__(self, provider, args, config, obj):
    super(Launch, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Launch"""
    if self.obj['plan']:
      for plan, pack in self.config_obj.plans().iteritems():
        for c in pack:
          print c
    else:
      self.launch_and_bootstrap(self.obj['name'])
      
  def launch_and_bootstrap(self, name):
    if not self.provider.get(name):
      instance = self.provider.launch(self.obj)
      if instance:
        self.provider.bootstrap(instance, self.obj)
    else:
      print "Instance ({0}) already running".format(name)