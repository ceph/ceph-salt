health-ok.sh
============

ceph-bootstrap integration test automation script


Overview
--------

This bash script contains integration tests for validating Ceph deployments
done with ceph-bootstrap.

The idea is to run this script with the appropriate arguments on the
Salt Master node after using ceph-bootstrap to deploy a cluster.

The script makes a number of assumptions, as listed under "Assumptions", below.

On success (HEALTH_OK is reached, sanity tests pass), the script returns 0.
On failure, for whatever reason, the script returns non-zero.

The script produces verbose output on stdout, which can be captured for later
forensic analysis.

Though referred to as a bash script, ``health-ok.sh`` is only the entry point.
That file uses the bash internal ``source`` to run several helper scripts, which
are located in the ``common/`` subdirectory.


Assumptions
-----------

The script makes the following assumptions:

1. the script is being run on the Salt Master of a Ceph cluster deployed using
   ceph-bootstrap
2. the script is being run as root
3. the Ceph admin keyring is installed in the usual way, so the root user can
   see and use the keyring


Caveats
-------

The following caveats apply:

1. Ceph will not work properly unless the nodes have (at least) short hostnames. That means the health-ok.sh script won't pass, either. There are two options: ``/etc/hosts`` or DNS
