from boto.ec2.blockdevicemapping import BlockDeviceType
from boto.ec2.blockdevicemapping import BlockDeviceMapping

def block_mappings(flavor):
  mapping = BlockDeviceMapping()
  if flavor == "hs1.8xlarge":
    for i in range(0, 24):
      eph = BlockDeviceType()
      eph.ephemeral_name = "ephemeral%d" % i
      device = "/dev/sd%c1" % chr(ord('b') + i)
      mapping[device] = eph
  return mapping
