
{% import 'macros.yml' as macros %}

{% if 'latency' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Configuring tuned latency') }}

install tuned:
  pkg.installed:
    - pkgs:
      - tuned
    - failhard: true

/etc/tuned/ceph-latency/tuned.conf:
  file.managed:
    - source: salt://ceph-salt/apply/files/latency.conf.j2
    - template: jinja
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - failhard: true

start tuned for latency profile:
  service.running:
    - name: tuned
    - enable: True
    - failhard: true

apply latency profile:
  cmd.run:
    - name: 'tuned-adm profile ceph-latency'
    - failhard: true

{{ macros.end_stage('Configuring tuned latency') }}

{% endif %}

tuned latency:
  test.nop
