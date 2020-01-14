{% if pillar['ceph-salt']['time_server'].get('enabled', True) %}

install chrony:
  pkg.installed:
    - pkgs:
      - chrony
    - refresh: True
    - fire_event: True

service_reload:
  module.run:
    - name: service.systemctl_reload

/etc/chrony.conf:
  file.managed:
    - source:
        - salt://ceph-salt/files/chrony.conf.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0644'
    - makedirs: True
    - backup: minion
    - fire_event: True

start chronyd:
  service.running:
    - name: chronyd
    - enable: True
    - fire_event: True

{% endif %}

prevent empty file:
  test.nop
