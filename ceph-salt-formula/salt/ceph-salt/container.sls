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

{{ macros.begin_step('Login into registries') }}

{% set registries = pillar['ceph-salt'].get('container', {}).get('auth', []) -%}
{%- for reg in registries %}
create ceph-salt-registry-password-{{loop.index}}:
  file.managed:
    - name: /tmp/ceph-salt-registry-password-{{loop.index}}
    - user: root
    - group: root
    - mode: '0600'
    - contents_pillar: ceph-salt:container:auth:{{loop.index - 1}}:password
    - failhard: True

login into registry {{loop.index}}:
  cmd.run:
    - name: |
        podman login \
{%- if 'tls_verify' in reg %}
        --tls-verify={{reg.tls_verify}} \
{%- endif %}
        -u={{reg.username}} \
        --password-stdin < /tmp/ceph-salt-registry-password-{{loop.index}} \
        {{reg.registry}}
    - failhard: True
{%- endfor %}

{{ macros.end_step('Login into registries') }}

{{ macros.end_stage('Set up container environment') }}
