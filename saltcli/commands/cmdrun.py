from saltcli.commands import Command

class Cmdrun(Command):
  def __init__(self, environment):
    super(Cmdrun, self).__init__(environment)

  def run(self):
    command = self.environment.opts['__args']
    if command is None:
      print "You must pass a command to run"
    else:
      self.environment.provider.cmdrun(command)