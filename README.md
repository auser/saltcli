Salt-CLI
==================================

Simple command-line man-handling of SaltStack. Manage SaltStack from the comfort of your own development machine.


Sample configuration:

    machines:
      master:
        roles:
          - saltmaster
      monitor:
        roles:
          - monitor
      hadoop:
        roles:
          - hadoop_master
          - hadoop_slave
          - hbase_master
          - zookeeper
          - elasticsearch
          - hbase_slave


    providers:
      aws:
        ssh_username: ubuntu
        keyname: keyname-dev
        region: us-east-1
        availability_zone: us-east-1b

        machines:
          default:
            flavor: m1.small
            image_id: ami-e4770b8d
            region: us-east-1
            ports: 
              tcp:
                '0.0.0.0/0':
                  - 22
                  - 4505
          master:
            group: saltmaster
            ports:
              tcp:
                '0.0.0.0/0':
                  - 22
                monitor:
                  - 4505
                  - 4506
                '*':
                  - 2202
            user_data:
              |
                #!/bin/bash -ex
                echo "LAUNCHING WITH USER_DATA"
                touch "/tmp/ran_userdata"
          monitor: &monitor
            flavor: m1.large
            availability_zone: us-east-1d
            region: us-east-1
            user_data: ./deploy/sample_userdata.sh
            ports:
              udp:
                '0.0.0.0/0':
                  - 514
                  - 12201
                master:
                  - 80
                '*':
                  - 2202
              tcp:
                '0.0.0.0/0':
                  - 80
                  - 514
                '*':
                  - 2003
                  - 2004
          hadoop: &hadoop
            group: hadoop
            flavor: m1.xlarge
            ports:
              tcp:
                '0.0.0.0/0':
                  - 54310
