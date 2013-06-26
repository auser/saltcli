from saltcli.commands import Command

class Highstate(Command):
  def __init__(self, environment):
    super(Highstate, self).__init__(environment)
    
  def run(self):
    for name, inst in self.environment.instances.iteritems():
      inst.highstate()