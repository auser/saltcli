import sys, os, shutil
import time
from fabric.api import env
import tempfile
import salt.crypt

def build_fabric_env(insts, config={}):
  if not isinstance(insts, list):
    insts = [insts]
  env.hosts         = [inst.ip_address() for inst in insts if inst != None]
  env.key_filename  = inst.key_filename()
  env.user          = inst.ssh_username()
  env.port          = inst.ssh_port()
  return env

def gen_keys(keysize=2048):
    '''
    Generate Salt minion keys and return them as PEM file strings
    '''
    # Mandate that keys are at least 2048 in size
    if keysize < 2048:
        keysize = 2048
    tdir = tempfile.mkdtemp()

    salt.crypt.gen_keys(tdir, 'minion', keysize)
    priv_path = os.path.join(tdir, 'minion.pem')
    pub_path = os.path.join(tdir, 'minion.pub')
    with salt.utils.fopen(priv_path) as fp_:
        priv = fp_.read()
    with salt.utils.fopen(pub_path) as fp_:
        pub = fp_.read()
    shutil.rmtree(tdir)
    return priv, pub

## Straight from salt
def get_colors():
    '''
    Return the colors as an easy to use dict, pass False to return the colors
    as empty strings so that they will not be applied
    '''
    colors = {
        'BLACK': '\033[0;30m',
        'DARK_GRAY': '\033[1;30m',
        'LIGHT_GRAY': '\033[0;37m',
        'BLUE': '\033[0;34m',
        'LIGHT_BLUE': '\033[1;34m',
        'GREEN': '\033[0;32m',
        'LIGHT_GREEN': '\033[1;32m',
        'CYAN': '\033[0;36m',
        'LIGHT_CYAN': '\033[1;36m',
        'RED': '\033[0;31m',
        'LIGHT_RED': '\033[1;31m',
        'PURPLE': '\033[0;35m',
        'LIGHT_PURPLE': '\033[1;35m',
        'BROWN': '\033[0;33m',
        'YELLOW': '\033[1;33m',
        'WHITE': '\033[1;37m',
        'DEFAULT_COLOR': '\033[00m',
        'RED_BOLD': '\033[01;31m',
        'ENDC': '\033[0m',
    }

    return colors