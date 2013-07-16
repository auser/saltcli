class Instance(object):
  def __init__(self, name, instance_options, environment):
    super(Instance, self).__init__()
    self.name = name
    self.environment = environment
    self.instance_name = "{0}-{1}".format(self.environment.environment, self.name)
    self.instance_options = instance_options
    self.roles = instance_options.get('roles', [])
    
  ## Get this instance
  def get(self):
    return self.environment.provider.get(self.instance_name)
    
  ## Keyname
  def keyname(self):
    return self.environment.provider.config.get('keyname', None)
    
  def key_filename(self):
    return self.environment.provider.config.get('key_file', None)
    
  def ssh_username(self):
    return self.environment.provider.config.get('ssh_username', 'root')
  
  def ssh_port(self):
    return self.environment.provider.config.get('port', 22)
    
  ## Open an ssh shell
  def open_ssh_shell(self):
    self.environment.ssh.open_shell(self)
    
  ## Launch this instance
  def launch(self):
    self.environment.provider.launch([self])
    
  ## Teardown this instance
  def teardown(self):
    self.environment.provider.teardown(self)
    
  ## Highstate this instance
  def highstate(self):
    self.environment.provider.highstate(self)
    
  ## Bootstrap this instance
  def bootstrap(self):
    self.environment.provider.bootstrap([self])
  
  ## Is this the master instance?
  def ismaster(self):
    return self.name == "master"
  
  ## IP Address
  def ip_address(self):
    return self.get().ip_address
    
  def private_ip_address(self):
    return self.get().private_ip_address
  
  def placement(self):
    return self.get().placement
  
  ## Upload
  def upload(self, local_file, remote_file):
    self.environment.ssh.upload(self, local_file, remote_file)
  def upload_file(self, local_file, remote_file):
    self.environment.ssh.upload_file(self, local_file, remote_file)