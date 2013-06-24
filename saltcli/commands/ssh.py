from saltcli.commands import Command


class Ssh(Command):
  """docstring for ssh"""
  def __init__(self, provider, args, config, obj):
    super(Ssh, self).__init__(provider, args, config, obj)
    
  def run(self):
    """ssh"""
    inst = self.provider.get(self.obj['name'])
    if inst:
      self.provider.ssh.open_shell(inst, self.obj)
    else:
      print "Machine {0} is not running or could not be found".format(self.obj['name'])