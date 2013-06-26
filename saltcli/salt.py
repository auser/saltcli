import sys
from saltcli.models.environment import Environment
from saltcli.utils.cli import get_command

def run(working_opts):
  """Kick off"""
  environment = Environment(working_opts)
  
  command = get_command(working_opts['command'])
  command(environment)

def _load_config(conf_file):
  return Config(conf_file)
  
def known_providers():
  """All know providers"""
  return ['aws']

def known_commands():
  """All known commands"""
  return ('launch', 'list', 'teardown', 'ssh', 'upload', 'bootstrap', 'highstate', 'empty')