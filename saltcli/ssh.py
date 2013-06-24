from fabric.api import run, env, put, local, sudo
from subprocess import call
from fabric.tasks import execute
from fabric.operations import open_shell

class Ssh(object):
  """docstring for Ssh"""
  def __init__(self, config):
    super(Ssh, self).__init__()
    self.config = config

  def open_shell(self, inst, obj={}):
    env = self._env(inst)
    cmd = 'ssh {user}@{host} {opts}'.format(
      user = env.user,
      host = env.hosts[0],
      opts=self._ssh_opts_str(env),
    )
    print "Running: {0}".format(cmd)
    call(cmd, shell=True)
    
  def run_command(self, inst, cmd, obj={}):
    env = self._env(inst)
    def _run_command():
      run("{0}".format(cmd))
    execute(_run_command, hosts=env.hosts)
    
  def sudo_command(self, inst, cmd, obj={}):
    env = self._env(inst)
    def _run_command():
      sudo("{0}".format(cmd))
    execute(_run_command, hosts=env.hosts)
    
  def upload(self, inst, local_file, remote_file='/srv/salt', obj={}):
    env = self._env(inst)
    if isinstance(local_file, list):
      local_file = local_file[0]
    if isinstance(remote_file, list):
      remote_file = remote_file[0]
    cmd = "{rsync} {local} {user}@{host}:{remote}".format(
      rsync=self._rsync_opts(env),
      user=env.user,
      local=local_file,
      host=env.hosts[0],
      remote=remote_file,
    )
    
    def prepare_upload():
      sudo("mkdir -p {remote}".format(remote=remote_file))
      sudo("chown -R {user}:{user} {remote}".format(user=env.user, remote=remote_file))

    execute(prepare_upload, hosts=env.hosts)
    
    print "Running: {0}".format(cmd)
    call(cmd, shell=True)
  
  ## SSH Options
  def _ssh_opts_str(self, env):
    return " ".join([
      '-p', str(env.port),
      '-o', 'LogLevel=FATAL',
      '-o', 'StrictHostKeyChecking=no',
      '-o', 'UserKnownHostsFile=/dev/null',
      '-o', 'ForwardAgent=yes',
      '-i', "'{0}'".format(env.key_filename),
    ])
  
  ## RSYNC options
  def _rsync_opts(self, env):
    return " ".join([
      'rsync', '-az', '-v',
      '--exclude ".git"',
      '-e "ssh {0}"'.format(self._ssh_opts_str(env)),
    ])
    
  def _env(self, inst):
    env.hosts = [inst.ip_address]
    env.key_filename = self.config['key_file']
    env.user = self.config.get('ssh_username', 'root')
    env.port = self.config.get('ssh_port', 22)
    return env
    
  def _execute(self, cmd, **kwargs):
    print "cmd: {0} {1}".format(cmd, kwargs)
    execute(cmd, **kwargs)