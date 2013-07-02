from saltcli.commands import Command

class Overstate(Command):
  def __init__(self, environment):
    super(Overstate, self).__init__(environment)
    
  def run(self):
    self.environment.provider.overstate(self.environment.instances)