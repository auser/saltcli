from saltcli.commands import Command

class Cmdrun(Command):
  def __init__(self, environment):
    super(Cmdrun, self).__init__(environment)

  def run(self):
    print self.config
    # self.environment.provider.highstate(self.environment.instances)