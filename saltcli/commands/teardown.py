from saltcli.commands import Command
from saltcli.utils.cli import query_yes_no

class Teardown(Command):
  """docstring for Teardown"""
  def __init__(self, environment):
    super(Teardown, self).__init__(environment)
    
  def run(self):
    for inst in self.environment.instances:
      if not inst.ismaster():
        if self.environment.get('answer_yes', False) or query_yes_no("Are you sure you want to teardown {0}?".format(inst.name)):
          inst.teardown()
        else:
          print "Aborting..."
    # self.environment.instances
    # name = self.obj['name']
    # if self.obj['all']:
    #   for inst in self.provider.all():
    #     if inst.tags['name'] != "master":
    #       self.provider.teardown(inst)
    #   self.provider.teardown("{0}-{1}".format(self.obj['environment'], "master"))
    # else:
    #   if self.provider.get(name):
    #     if self.obj.get('answer_yes', False) or query_yes_no("Are you sure you want to tear down the {0} instance?".format(name)):
    #       self.provider.teardown(self.obj['name'])
    #     else:
    #       print "Aborting"
    #   else:
    #     print "No instance {0} was found, therefore it would be difficult to shut it down, wouldn't you agree?".format(name)