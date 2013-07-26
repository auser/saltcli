import sys
from saltcli.commands import Command

class Role(Command):
  def __init__(self, env):
    super(Role, self).__init__(env)
    
  def run(self):
    """Role"""
    roles = {}
    for inst in self.environment.instances:
      roles[inst] = self.environment.provider._get_instance_roles(inst)

    for name, roles in roles.items():
      print "{name}:".format(name=name)
      for _roles, arr in roles.items():
        for r in arr:
          print "       {r}".format(r=r)