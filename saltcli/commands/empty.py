from saltcli.commands import Command

class Empty(Command):
  def __init__(self, provider, args, config, obj):
    super(Empty, self).__init__(provider, args, config, obj)
    
  def run(self):
    return True