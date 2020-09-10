
{% import 'macros.yml' as macros %}

{% if 'latency' not in grains['ceph-salt']['roles'] and 'throughput' not in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Disable tuned') }}

stop tuned:
  service.dead:
    - name: tuned
    - enable: False
    - failhard: True

remove tuned ceph latency:
  file.absent:
    - name: /etc/tuned/ceph-latency/
    - failhard: True

remove tuned ceph throughput:
  file.absent:
    - name: /etc/tuned/ceph-throughput/
    - failhard: True

remove tuned ceph mon:
  file.absent:
    - name: /etc/tuned/ceph-mon/
    - failhard: True

remove tuned ceph mgr:
  file.absent:
    - name: /etc/tuned/ceph-mgr/
    - failhard: True

remove tuned ceph osd:
  file.absent:
    - name: /etc/tuned/ceph-osd/
    - failhard: True

{{ macros.end_stage('Disable tuned') }}

{% endif %}

tuned off:
  test.nop
