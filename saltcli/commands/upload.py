import os
from saltcli.commands import Command

class Upload(Command):
  """docstring for Launch"""
  def __init__(self, provider, args, config, obj):
    super(Upload, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Upload"""
    inst = self.provider.get(self.obj['name'])
    args = self.args
    if len(args) == 0:
      working_dir = os.getcwd()
      args = [os.path.join(working_dir, "deploy", "salt/")]
      
    self.provider.ssh.upload(inst, *args)