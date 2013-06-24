from saltcli.commands import Command

class Teardown(Command):
  """docstring for Teardown"""
  def __init__(self, provider, args, config, obj):
    super(Teardown, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Teardown"""
    self.provider.teardown(self.obj['name'])