#!/bin/sh

apt-get -y update
apt-get -y install docker.io

gcloud -q docker -- pull {{docker_image}}

docker run {{docker_image}} {{container_args}}

# TODO might want to copy /var/log/daemon.log to GCS for useful debugging info

gcloud -q compute instances delete --zone={{zone_id}} {{instance_name}}
