#!/usr/bin/env python

import boto
import sys
import os

this_dir = os.path.dirname(os.path.realpath(__file__))

user_data = open(os.path.join(this_dir, 'bootstrap', 'master.sh'))

try:  
   access_key = os.environ['AWS_ACCESS_KEY_ID']
except KeyError: 
   print "Please set the environment variable AWS_SECRET_ACCESS_KEY"
   sys.exit(1)

try:  
   secret_key = os.environ['AWS_SECRET_ACCESS_KEY']
except KeyError: 
   print "Please set the environment variable AWS_SECRET_ACCESS_KEY"
   sys.exit(1)

conn = boto.connect_ec2(access_key, secret_key)

print "conn: {0}".format(conn)

# reservation = conn.run_instances(image_id=<ami_id>,
#                                  key_name=<key_name>,
#                                  user_data=user_data.read())
