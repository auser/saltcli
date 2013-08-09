import yaml

class Config(object):
  def __init__(self, conf_file):
    super(Config, self).__init__()
    self.conf_file = conf_file
    self.load_conf()
  
  def machines(self):
    return self.config.get('machines', [])
  
  def yaml(self):
    return self.config  
  
  def load_conf(self):
    stream = open(self.conf_file)
    self.config = yaml.load(stream)
    return self.config