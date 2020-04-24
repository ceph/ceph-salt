{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Prepare to bootstrap the Ceph cluster') }}

{{ macros.begin_step('Install cephadm package') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - cephadm
    - failhard: True

/var/log/ceph:
  file.directory:
    - user: root
    - group: root
    - mode: '0770'
    - makedirs: True
    - failhard: True

/etc/ceph/ceph:
  file.directory:
    - user: root
    - group: root
    - mode: '0770'
    - makedirs: True
    - failhard: True

{{ macros.end_step('Install cephadm package') }}

{{ macros.begin_step('Run "cephadm check-host"') }}

have cephadm check the host:
  cmd.run:
    - name: |
        cephadm check-host
    - failhard: True

{{ macros.end_step('Run "cephadm check-host"') }}

{{ macros.begin_step('Download ceph container image') }}
download ceph container image:
  cmd.run:
    - name: |
        cephadm --image {{ pillar['ceph-salt']['container']['images']['ceph'] }} pull
    - failhard: True
{{ macros.end_step('Download ceph container image') }}

{{ macros.end_stage('Prepare to bootstrap the Ceph cluster') }}
