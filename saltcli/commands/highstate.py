from saltcli.commands import Command

class Highstate(Command):
  def __init__(self, provider, args, config, obj):
    super(Highstate, self).__init__(provider, args, config, obj)
    
  def run(self):
    self.provider.highstate(self.obj)