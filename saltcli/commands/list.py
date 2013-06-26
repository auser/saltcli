from saltcli.commands import Command
from saltcli.utils.utils import get_colors

class List(Command):
  """docstring for Launch"""
  def __init__(self, environment):
    super(List, self).__init__(environment)
    
  def run(self):
    """Launch"""
    instances = self.environment.provider.all()
    if len(instances) > 0:
      for inst in instances:
        print """{name}:
    id: {id}
    ip_address: {ip}
    environment: {environment}""".format( id=inst.id, 
                    ip=inst.ip_address, 
                    name=inst.tags.get('instance_name', None), 
                    environment=inst.tags.get('environment', None))
    else:
      colors = get_colors()
      self.environment.debug("{0}No instances found. You have an empty cluster, my friend. Try launching one...{1[ENDC]}".format(
        colors['RED'], colors
      ))