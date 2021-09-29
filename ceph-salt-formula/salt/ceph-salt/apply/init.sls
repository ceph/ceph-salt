{% if grains['id'] in pillar['ceph-salt']['minions']['all'] %}

# This little hack ensures that the cephadm package is installed at jinja
# *compile* time on all salt minions.  The cephadm package itself ensures
# the cephadm user and group are created, so we'll be able to rely on those
# things existing later when the states are applied to pick up the correct
# home directory, gid, etc.  The fact that the next line is a comment
# doesn't matter, it'll still be expanded at jinja compile time and the
# package will be installed correctly (either that or it'll fail with an
# appropriate error message if the package can't be installed for some
# reason).
#
# {{ salt['pkg.install']('cephadm') }}
#
# One irritation is that ideally, cephadm would only be installed on nodes
# with the cephadm role.  Unfortunately, ceph-salt uses the cephadm user's
# ssh keys to ssh between nodes to do things like check if grains are set
# on remote hosts (e.g. when setting up time sync).  This means we need the
# cephadm package installed everywhere to ensure the user and home directory
# are present.

include:
    - ..reset
    - ..common.sshkey
    - .sysctl
    - .tuned-off
    - .tuned-latency
    - .tuned-throughput
    - .software
    - .container
    - .apparmor
    - .time-prep
    - .time-sync
    - .cephtools
    - .cephbootstrap
    - .cephconfigure
    - .cephorch
    - .ceph-admin
    - .apply-end

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
