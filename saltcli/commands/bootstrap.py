import os
from fabric.api import sudo
from fabric.tasks import execute
from saltcli.commands import Command

class Bootstrap(Command):
  def __init__(self, env):
    super(Bootstrap, self).__init__(env)
    
  def run(self):
    """Bootstrap"""
    self.environment.provider.bootstrap(self.environment.instances)
