from saltcli.commands import Command

class Highstate(Command):
  def __init__(self, environment):
    super(Highstate, self).__init__(environment)
    
  def run(self):
    for inst in self.environment.instances:
      inst.highstate()