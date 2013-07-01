import os
from saltcli.commands import Command
from saltcli.utils.utils import get_colors
from saltcli.utils.cli import query_yes_no

class Key(Command):
  def __init__(self, environment):
    super(Key, self).__init__(environment)
    
  def run(self):
    """Launch"""
    conn = self.environment.provider.conn
    
    if len(self.environment.opts['__args']) > 0:
      cmd = self.environment.opts['__args'].pop()
    else:
      cmd = "list"
      
    keyname = self.environment.provider.config['keyname']
    keypair = conn.get_key_pair(keyname)
    
    if cmd == 'list':
      for keypair in conn.get_all_key_pairs():
        print "keypair: {0}".format(keypair.name)
    elif cmd == 'delete':
      if keypair is not None:
        if self.environment.opts.get('answer_yes', False) or query_yes_no(
        """You are about to delete the keypair {0}.
          Are you sure you want to continue?
        
          This will also remove the keypair from your ~/.ec2/directory""".format(keyname)):
          keyfile = self.environment.provider.config.get('key_file', None)
          keypair.delete()
          if keyfile is not None and os.path.exists(keyfile):
            os.remove(keyfile)
      
    # if len(instances) > 0:
#       for inst in instances:
#         print """{name}:
#     id: {id}
#     ip_address: {ip}
#     environment: {environment}""".format( id=inst.id, 
#                     ip=inst.ip_address, 
#                     name=inst.tags.get('instance_name', None), 
#                     environment=inst.tags.get('environment', None))
#     else:
#       colors = get_colors()
#       self.environment.debug("{0}No instances found. You have an empty cluster, my friend. Try launching one...{1[ENDC]}".format(
#         colors['RED'], colors
#       ))