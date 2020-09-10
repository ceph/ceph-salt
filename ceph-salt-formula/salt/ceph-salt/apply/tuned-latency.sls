
{% import 'macros.yml' as macros %}

{% if 'latency' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Configure tuned latency') }}

install tuned:
  pkg.installed:
    - pkgs:
      - tuned
    - failhard: True

/etc/tuned/ceph-latency/tuned.conf:
  file.managed:
    - source: salt://ceph-salt/apply/files/latency.conf.j2
    - template: jinja
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - failhard: True

start tuned for latency profile:
  service.running:
    - name: tuned
    - enable: True
    - failhard: True

apply latency profile:
  cmd.run:
    - name: 'tuned-adm profile ceph-latency'
    - failhard: True

{{ macros.end_stage('Configure tuned latency') }}

{% endif %}

tuned latency:
  test.nop
