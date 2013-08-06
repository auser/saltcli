import boto, os

# Set up the keypair
def setup_keypair(conn, node, config):
  # Get the connection corresponding to this node
  # conn = regions[node.region]
  inst_key_name       = key_name(conn, node, config)
  inst_key_filename   = key_filename(conn, node, config)

  # Get the fingerprint of the local key file (assuming it exists)
  fingerprint = ""
  if os.path.exists(inst_key_filename):
    fingerprint = _key_fingerprint(inst_key_filename)

  # Now look for the key on EC2
  key = _lookup_ec2_key(conn, inst_key_name)
  if key and key.fingerprint == fingerprint:
    # The key exists and matches our local fingerprint; we're set to go
    print "Key %s already exists and matches EC2 fingerprint" % (inst_key_name)
    return inst_key_name

  else:
    # Either the key doesn't exist or doesn't match our local key; either way
    # we need to re-create the key and save it to disk
    print "Recreating key..."
    if key:
      conn.delete_key_pair(inst_key_name)
    key = conn.create_key_pair(inst_key_name)

    # Ensure the target directory for keys exists
    if not os.path.exists(config['key_dir']):
      os.makedirs(config['key_dir'])

    # Ensure the target file doesn't already exist
    if os.path.exists(inst_key_filename):
      os.remove(inst_key_filename)

    # Save the key and set perms
    key.save(config['key_dir'])
    os.chmod(inst_key_filename, 0600)
    return inst_key_name

def _key_fingerprint(key_filename):
  import subprocess
  try:
    fingerprint = subprocess.check_output(["ec2-fingerprint-key", key_filename],
                                          stderr = subprocess.STDOUT)
    return fingerprint.strip()
  except subprocess.CalledProcessError as e:
    print "Failed to pull fingerprint for %s: %s\n" % (key_filename, e.output)
    return ""

def key_name(conn, node, config):
  return "%s-%s" % (conn.region, config['keyname'])

def key_filename(conn, node, config):
  return os.path.join(config['key_dir'], key_name(conn, node, config) + ".pem")

def _lookup_ec2_key(conn, key_name):
  try:
    [key] = conn.get_all_key_pairs(keynames = [key_name])
    return key
  except boto.exception.EC2ResponseError as err:
    if err.error_code == "InvalidKeyPair.NotFound":
      return None
    else:
      raise err