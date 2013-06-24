from saltcli.commands import Command

class List(Command):
  """docstring for Launch"""
  def __init__(self, provider, args, config, obj):
    super(List, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Launch"""
    instances = self.provider.list_instances()
    for inst in instances:
      print """{name}:
  id: {id}
  ip_address: {ip}
  environment: {environment}""".format( id=inst.id, 
                  ip=inst.ip_address, 
                  name=inst.tags.get('original_name', None), 
                  environment=inst.tags.get('environment', None))