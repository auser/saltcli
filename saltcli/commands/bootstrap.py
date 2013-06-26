import os
from fabric.api import sudo
from fabric.tasks import execute
from saltcli.commands import Command

class Bootstrap(Command):
  def __init__(self, provider, args, config, obj):
    super(Bootstrap, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Bootstrap"""
    if self.obj['all']:
      for inst in self.provider.all():
        conf = self.obj.copy()
        name, instance_name = inst.tags['name'], inst.tags['instance_name']
        if instance_name != "master":
          conf['instance_name'] = instance_name
          conf['name'] = name
          self.provider.bootstrap(inst, conf)
    else:
      inst = self.provider.get(self.obj['name'])
      self.provider.bootstrap(inst, self.obj)