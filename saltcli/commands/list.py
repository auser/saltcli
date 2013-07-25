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
      for inst_d in instances:
        inst = inst_d['instance']
        print """{name}:
    id: {id}
    ip_address: {ip}
    region: {placement}
    availability zone: {az}
    environment: {environment}""".format( id=inst.id, 
                    ip=inst.ip_address, 
                    name=inst.tags.get('name', None),
                    placement=inst_d['region_name'],
                    az=inst.placement,
                    environment=inst.tags.get('environment', None))
    else:
      colors = get_colors()
      self.environment.debug("{0}No instances found. You have an empty cluster, my friend. Try launching one...{1[ENDC]}".format(
        colors['RED'], colors
      ))