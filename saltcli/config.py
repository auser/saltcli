import yaml

def load_config(path):
  """Load a config file at at path"""
  stream = open(path)
  print yaml.load(stream)
  
def load_credentials():
  """Load credentials"""
  pass
