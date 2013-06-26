class Instance(object):
  def __init__(self, name, environment):
    super(Instance, self).__init__()
    self.name = name
    self.environment = environment
    self.instance_name = "{0}-{1}".format(self.environment.environment, self.name)
    
  ## Get this instance
  def get(self):
    self.environment.provider.get(self.instance_name)
    
  ## Keyname
  def keyname(self):
    return self.environment.provider.config.get('keyname', None)
    
  ## Launch this instance
  def launch(self):
    print 'launch'
    
  ## Teardown this instance
  def teardown(self):
    self.environment.provider.teardown(self)
  
  ## Is this the master instance?
  def ismaster(self):
    return self.name == "master"
  
  ## IP Address
  def ip_address(self):
    self.get().ip_address