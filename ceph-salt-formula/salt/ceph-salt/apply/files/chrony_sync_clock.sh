#!/bin/bash
set -e
# address https://github.com/ceph/ceph-salt/issues/238
# by waiting up to 5 minutes for chrony to see its sources
for trywait in "$(seq 0 9)" ; do
    chronyc 'burst 4/4' && break || true
    sleep 30
done
sleep 15
chronyc makestep
chronyc waitsync 60 0.04
