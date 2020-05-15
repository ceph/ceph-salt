#!/bin/bash
set -e
chronyc 'burst 4/4'
sleep 15
chronyc makestep
chronyc waitsync 60 0.04
