{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Set up container environment') }}

{% if pillar['ceph-salt']['container']['registries_enabled'] %}

{{ macros.begin_step('Configure container image registries') }}

/etc/containers/registries.conf:
  file.managed:
    - source:
        - salt://ceph-salt/files/registries.conf.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0644'
    - backup: minion
    - failhard: True

{{ macros.end_step('Configure container image registries') }}

{% endif %}

{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

{% if auth %}

{{ macros.begin_step('Login into registry') }}

create ceph-salt-registry-password:
  file.managed:
    - name: /tmp/ceph-salt-registry-password
    - user: root
    - group: root
    - mode: '0600'
    - contents_pillar: ceph-salt:container:auth:password
    - failhard: True

login into registry:
  cmd.run:
    - name: |
        podman login \
        -u={{ auth.get('username') }} \
        --password-stdin < /tmp/ceph-salt-registry-password \
        {{ auth.get('registry') }}
    - failhard: True

{{ macros.end_step('Login into registry') }}

{% endif %}

{{ macros.end_stage('Set up container environment') }}
