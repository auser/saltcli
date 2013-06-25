from saltcli.commands import Command
from saltcli.lib.utils import query_yes_no

class Teardown(Command):
  """docstring for Teardown"""
  def __init__(self, provider, args, config, obj):
    super(Teardown, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Teardown"""
    name = self.obj['name']
    if self.obj['all']:
      for inst in self.provider.list_instances():
        if inst.tags['name'] != "master":
          self.provider.teardown(inst)
      self.provider.teardown("{0}-{1}".format(self.obj['environment'], "master"))
    else:
      if self.provider.get(name):
        if self.obj.get('answer_yes', False) or query_yes_no("Are you sure you want to tear down the {0} instance?".format(name)):
          self.provider.teardown(self.obj['name'])
        else:
          print "Aborting"
      else:
        print "No instance {0} was found, therefore it would be difficult to shut it down, wouldn't you agree?".format(name)