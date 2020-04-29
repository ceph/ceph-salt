#!/bin/bash
set -e
chronyc 'burst 4/4'
sleep 15
chronyc makestep
chronyc waitsync 30 0.04
