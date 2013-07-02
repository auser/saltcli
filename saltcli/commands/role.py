import sys
from saltcli.commands import Command

class Role(Command):
  def __init__(self, env):
    super(Role, self).__init__(env)
    
  def run(self):
    """Role"""
    print "NOT YET IMPLEMENTED"