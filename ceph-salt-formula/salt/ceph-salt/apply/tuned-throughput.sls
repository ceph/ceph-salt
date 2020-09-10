
{% import 'macros.yml' as macros %}

{% if 'throughput' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Configure tuned throughput') }}

install tuned:
  pkg.installed:
    - pkgs:
      - tuned
    - failhard: True

/etc/tuned/ceph-throughput/tuned.conf:
  file.managed:
    - source: salt://ceph-salt/apply/files/throughput.conf.j2
    - template: jinja
    - makedirs: True
    - user: root
    - group: root
    - mode: 644
    - failhard: True

start tuned for throughput profile:
  service.running:
    - name: tuned
    - enable: True
    - failhard: True

apply throughput profile:
  cmd.run:
    - name: 'tuned-adm profile ceph-throughput'
    - failhard: True

{{ macros.end_stage('Configure tuned throughput') }}

{% endif %}

tuned throughput:
  test.nop
