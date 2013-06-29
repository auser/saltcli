import os
from saltcli.commands import Command

class Upload(Command):
  """docstring for Launch"""
  def __init__(self, environment):
    super(Upload, self).__init__(environment)
    
  def run(self):
    """Upload"""
    instance = self.environment.master_server()
    salt_dir = os.path.join(os.getcwd(), "deploy", "salt/")
    instance.upload(salt_dir, "/srv/salt")
