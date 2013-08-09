from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

def block_mappings(flavor):
  mapping = BlockDeviceMapping()
  if flavor == "hs1.8xlarge":
    for i in range(0, 23):
      eph = BlockDeviceType()
      eph.ephemeral_name = "ephemeral%d" % i
      device = "/dev/sd%c" % chr(ord('c') + i)
      mapping[device] = eph
  return mapping
