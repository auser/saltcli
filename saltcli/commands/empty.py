from saltcli.commands import Command

class Empty(Command):
  def __init__(self, environment):
    super(Empty, self).__init__(environment)

  def run(self):
    return True