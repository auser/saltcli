import os
from fabric.api import sudo
from fabric.tasks import execute
from saltcli.commands import Command

class Bootstrap(Command):
  def __init__(self, provider, args, config, obj):
    super(Bootstrap, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Bootstrap"""
    inst = self.provider.get(self.obj['name'])
    self.provider.bootstrap(inst, self.obj)