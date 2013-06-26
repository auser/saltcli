from saltcli.commands import Command
from saltcli.utils.cli import query_yes_no

class Teardown(Command):
  """docstring for Teardown"""
  def __init__(self, environment):
    super(Teardown, self).__init__(environment)
    
  def run(self):
    # This could be more efficient by sorting the master server to the end
    # but it works for now
    for name, inst in self.environment.instances.iteritems():
      if not inst.ismaster() and inst.get() != None:
        if self.environment.opts.get('answer_yes', False) or query_yes_no("Are you sure you want to teardown {0}?".format(inst.name)):
          inst.teardown()
        else:
          print "Aborting..."
    inst = self.environment.master_server()
    if inst:
      if self.environment.opts.get('answer_yes', False) or query_yes_no("Are you sure you want to teardown {0}?".format(inst.name)):
        inst.teardown()