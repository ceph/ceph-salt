{% if 'ceph-salt' in grains and grains['ceph-salt']['member'] %}

check safety:
   ceph_salt.check_safety:
     - failhard: True

check fsid:
   ceph_salt.check_fsid:
     - formula: ceph-salt.purge
     - failhard: True

remove clusters:
   ceph_orch.rm_clusters:
     - failhard: True

{% else %}

nothing to do in this node:
  test.nop

{% endif %}
