{% import 'macros.yml' as macros %}

{% if 'cephadm' in grains['ceph-salt']['roles'] %}

{{ macros.begin_stage('Prepare to bootstrap the Ceph cluster') }}

{{ macros.begin_step('Install cephadm and other packages') }}

install cephadm:
  pkg.installed:
    - pkgs:
        - cephadm
{% if 'admin' in grains['ceph-salt']['roles'] %}
        - ceph-base
        - ceph-common
{% endif %}
    - failhard: True

# in case any package instalation re-writes sudoers /etc/sudoers.d/<ssh_user>
{{ macros.sudoers('configure sudoers after package instalation') }}

{% if grains['id'] == pillar['ceph-salt'].get('bootstrap_minion') %}

/var/log/ceph:
  file.directory:
    - user: ceph
    - group: ceph
    - mode: '0770'
    - makedirs: True
    - failhard: True
{% endif %}

{{ macros.end_step('Install cephadm and other packages') }}

{{ macros.begin_step('Run "cephadm check-host"') }}

have cephadm check the host:
  cmd.run:
    - name: |
        cephadm check-host
    - failhard: True

{{ macros.end_step('Run "cephadm check-host"') }}

{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

{% if auth %}

{{ macros.begin_step('Login into registry') }}

create ceph-salt-registry-json:
  file.managed:
    - name: /tmp/ceph-salt-registry-json
    - source:
        - salt://ceph-salt/files/registry-login-json.j2
    - template: jinja
    - user: root
    - group: root
    - mode: '0600'
    - backup: minion
    - failhard: True

login into registry:
  cmd.run:
    - name: |
        cephadm registry-login \
        --registry-url {{ auth.get('registry') }} \
        --registry-username {{ auth.get('username') }} \
        --registry-password {{ auth.get('password') }}
    - failhard: True

{{ macros.end_step('Login into registry') }}

{% endif %}

{{ macros.begin_step('Download ceph container image') }}
download ceph container image:
  ceph_orch.pull_image:
    - failhard: True
{{ macros.end_step('Download ceph container image') }}

{{ macros.end_stage('Prepare to bootstrap the Ceph cluster') }}

{% endif %}
