from saltcli.commands import Command

class Launch(Command):
  """docstring for Launch"""
  def __init__(self, provider, args, config, obj):
    super(Launch, self).__init__(provider, args, config, obj)
    
  def run(self):
    """Launch"""
    if self.obj['plan']:
      for plan, pack in self.config_obj.plans().iteritems():
        for c in pack:
          for name, opts in c.items():
            conf = self.obj.copy()
            if opts['roles']:
              conf['roles'] = opts['roles']
            conf['original_name'] = name
            conf['name'] = conf['environment'] + "-" + name
            self.launch_and_bootstrap(conf['name'], conf)
            
      self.provider.highstate(self.obj)
    else:
      self.launch_and_bootstrap(self.obj['name'], self.obj)
      
  def launch_and_bootstrap(self, name, conf={}):
    if not self.provider.get(name):
      instance = self.provider.launch(conf)
      if instance:
        self.provider.bootstrap(instance, conf)
    else:
      print "Instance ({0}) already running".format(name)