
{% import 'macros.yml' as macros %}

{% if 'latency' not in grains['ceph-salt']['roles'] and 'throughput' not in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Disabling tuned') }}

stop tuned:
  service.dead:
    - name: tuned
    - enable: False
    - failhard: true

/etc/tuned/ceph-latency/:
  file.absent

/etc/tuned/ceph-throughput/:
  file.absent

/etc/tuned/ceph-mon/:
  file.absent

/etc/tuned/ceph-mgr/:
  file.absent

/etc/tuned/ceph-osd/:
  file.absent

{{ macros.end_stage('Disabling tuned') }}

{% endif %}

tuned off:
  test.nop
