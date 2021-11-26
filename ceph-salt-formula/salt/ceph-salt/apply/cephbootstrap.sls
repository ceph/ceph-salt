{% import 'macros.yml' as macros %}

{% if grains['id'] == pillar['ceph-salt'].get('bootstrap_minion') and pillar['ceph-salt'].get('execution', {}).get('deployed') != True %}

{{ macros.begin_stage('Prepare to bootstrap the Ceph cluster') }}

/var/log/ceph:
  file.directory:
    - user: ceph
    - group: ceph
    - mode: '0770'
    - makedirs: True
    - failhard: True

{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

{% if auth %}

{{ macros.begin_step('Login into registry') }}

login into registry:
  cmd.run:
    - name: |
        cephadm registry-login \
        --registry-json /tmp/ceph-salt-registry-json
    - failhard: True

{{ macros.end_step('Login into registry') }}

{% endif %}

{{ macros.begin_step('Download ceph container image') }}
download ceph container image:
  cmd.run:
    - name: |
        cephadm --image {{ pillar['ceph-salt']['container']['images']['ceph'] }} pull
    - failhard: True
{{ macros.end_step('Download ceph container image') }}

{{ macros.end_stage('Prepare to bootstrap the Ceph cluster') }}

{{ macros.begin_stage('Bootstrap the Ceph cluster') }}

{% set bootstrap_ceph_conf = pillar['ceph-salt'].get('bootstrap_ceph_conf', {}) %}
{% set bootstrap_ceph_conf_tmpfile = "/tmp/bootstrap-ceph.conf" %}
{% set bootstrap_spec_yaml_tmpfile = "/tmp/bootstrap-spec.yaml" %}
{% set my_hostname = salt['ceph_salt.hostname']() %}

create static bootstrap yaml:
  cmd.run:
    - name: |
        echo -en "" > {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_type: mgr\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_name: mgr\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "placement:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "    hosts:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "        - '{{ my_hostname }}'\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        >> foo
        echo -en "---\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_type: mon\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_name: mon\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "placement:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "    hosts:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "        - '{{ my_hostname }}:{{ pillar['ceph-salt']['bootstrap_mon_ip'] }}'\n" >> {{ bootstrap_spec_yaml_tmpfile }}

create bootstrap ceph conf:
  cmd.run:
    - name: |
        echo -en "" > {{ bootstrap_ceph_conf_tmpfile }}
{% for section, settings in bootstrap_ceph_conf.items() %}
        echo -en "[{{ section }}]\n" >> {{ bootstrap_ceph_conf_tmpfile }}
{% for setting, value in settings.items() %}
        echo -en "        {{ setting }} = {{ value }}\n" >> {{ bootstrap_ceph_conf_tmpfile }}
{% endfor %}
{% endfor %}
    - failhard: True

{{ macros.begin_step('Run "cephadm bootstrap"') }}

{% set dashboard_username = pillar['ceph-salt']['dashboard']['username'] %}
{% set dashboard_password = pillar['ceph-salt']['dashboard']['password'] %}
{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

{# --mon-ip is still required, even though we're also putting the Mon IP      #}
{# directly in the placement YAML (see https://tracker.ceph.com/issues/46782) #}
run cephadm bootstrap:
  cmd.run:
    - name: |
        CEPHADM_IMAGE={{ pillar['ceph-salt']['container']['images']['ceph'] }} \
        cephadm --verbose bootstrap \
                --mon-ip {{ pillar['ceph-salt']['bootstrap_mon_ip'] }} \
                --allow-fqdn-hostname \
                --apply-spec {{ bootstrap_spec_yaml_tmpfile }} \
                --config {{ bootstrap_ceph_conf_tmpfile }} \
                --container-init \
{%- if not pillar['ceph-salt']['dashboard']['password_update_required'] %}
                --dashboard-password-noupdate \
{%- endif %}
                --initial-dashboard-password {{ dashboard_password }} \
                --initial-dashboard-user {{ dashboard_username }} \
                --output-config /etc/ceph/ceph.conf \
                --output-keyring /tmp/ceph.client.admin.keyring \
{%- if auth %}
                --registry-json /tmp/ceph-salt-registry-json \
{%- endif %}
                --skip-monitoring-stack \
                --skip-prepare-host \
                --skip-pull \
                --ssh-private-key {{ salt['user.info']('cephadm').home }}/.ssh/id_rsa \
                --ssh-public-key {{ salt['user.info']('cephadm').home }}/.ssh/id_rsa.pub \
                --ssh-user cephadm \
{%- for arg, value in pillar['ceph-salt'].get('bootstrap_arguments', {}).items() %}
                --{{ arg }} {{ value if value is not none else '' }} \
{%- endfor %}
                > /var/log/ceph/cephadm.out 2>&1
    - env:
      - NOTIFY_SOCKET: ''
    - creates:
      - /etc/ceph/ceph.conf
    - failhard: True

{{ macros.end_step('Run "cephadm bootstrap"') }}

copy ceph.conf and keyring to any admin node:
  ceph_orch.copy_ceph_conf_and_keyring_to_any_admin:
    - failhard: True

remove temporary keyring:
  file.absent:
    - name: /tmp/ceph.client.admin.keyring
    - failhard: True

{{ macros.end_stage('Bootstrap the Ceph cluster') }}

{% endif %}
