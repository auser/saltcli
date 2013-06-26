from saltcli.commands import Command


class Ssh(Command):
  """docstring for ssh"""
  def __init__(self, environment):
    super(Ssh, self).__init__(environment)
    
  def run(self):
    """ssh"""
    name = self.environment.opts.get('name')[0]
    inst = self.environment.instances[name] ### Can only ssh into one machine at a time
    if inst.get() != None:
      inst.open_ssh_shell()
    else:
      print "Machine {0} is not running or could not be found".format(inst.name)