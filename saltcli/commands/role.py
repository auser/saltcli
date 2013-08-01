import sys
from saltcli.commands import Command

class Role(Command):
  def __init__(self, env):
    super(Role, self).__init__(env)
    
  def run(self):
    """Role"""
    roles = {}
    if len(self.environment.orig_opts['roles']) == 0:
      for inst in self.environment.instances:
        roles[inst] = self.environment.provider._get_instance_roles(inst)

      for name, roles in roles.items():
        print "{name}:".format(name=name)
        if roles is not None:
          for _roles, arr in roles.items():
            for r in arr:
              print "       {r}".format(r=r)
    else:
      roles_to_set = self.environment.orig_opts['roles']
      for inst in self.environment.instances:
        res = self.environment.provider._set_instance_roles(inst, roles_to_set)
        if res:
          print "Successfully set roles {0} to {1}".format(roles_to_set, inst)
        else:
          print "There was a problem"