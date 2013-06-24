import boto
import sys
import os

def launch(obj):
  """Launch"""
  print "Launch"
# this_dir = os.path.dirname(os.path.realpath(__file__))
# working_dir = os.getcwd()

# user_data = open(os.path.join(working_dir, 'bootstrap', 'master.sh'))

# conn = boto.connect_ec2(access_key, secret_key)

# print "conn: {0}".format(conn)

# reservation = conn.run_instances(image_id=<ami_id>,
#                                  key_name=<key_name>,
#                                  user_data=user_data.read())
