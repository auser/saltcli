from saltcli.commands import Command

class Launch(Command):
  """docstring for Launch"""
  def __init__(self, provider, args, config, obj):
    super(Launch, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Launch"""
    if not self.provider.get(self.obj['name']):
      instance = self.provider.launch(self.obj)
      if instance:
        self.provider.bootstrap(instance, self.obj)
    else:
      print "Instance ({0}) already running".format(self.obj['name'])