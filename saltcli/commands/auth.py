from saltcli.commands import Command

class Auth(Command):
  def __init__(self, environment):
    super(Auth, self).__init__(environment)

  def run(self):
    self.environment.provider.salt_auth(self.environment.instances)