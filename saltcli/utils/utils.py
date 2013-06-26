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
