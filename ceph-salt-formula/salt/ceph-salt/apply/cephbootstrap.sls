{% import 'macros.yml' as macros %}

{% if grains['id'] == pillar['ceph-salt'].get('bootstrap_minion') %}

{{ macros.begin_stage('Bootstrap the Ceph cluster') }}

{% set bootstrap_ceph_conf = pillar['ceph-salt'].get('bootstrap_ceph_conf', {}) %}
{% set bootstrap_ceph_conf_tmpfile = "/tmp/bootstrap-ceph.conf" %}
{% set bootstrap_spec_yaml_tmpfile = "/tmp/bootstrap-spec.yaml" %}

create static bootstrap yaml:
  cmd.run:
    - name: |
        echo -en "" > {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_type: mgr\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_name: mgr\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "placement:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "    hosts:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "        - '{{ grains['host'] }}'\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        >> foo
        echo -en "---\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_type: mon\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "service_name: mon\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "placement:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "    hosts:\n" >> {{ bootstrap_spec_yaml_tmpfile }}
        echo -en "        - '{{ grains['host'] }}:{{ pillar['ceph-salt']['bootstrap_mon_ip'] }}'\n" >> {{ bootstrap_spec_yaml_tmpfile }}

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

{{ macros.begin_step('Wait for other minions') }}
wait for other minions:
  ceph_salt.wait_for_grain:
    - grain: ceph-salt:execution:provisioned
    - hosts: {{ pillar['ceph-salt']['minions']['all'] }}
    - failhard: True
{{ macros.end_step('Wait for other minions') }}

{{ macros.begin_step('Run "cephadm bootstrap"') }}

{% set dashboard_username = pillar['ceph-salt']['dashboard']['username'] %}
{% set dashboard_password = pillar['ceph-salt']['dashboard']['password'] %}
{% set ssh_user = pillar['ceph-salt']['ssh']['user'] %}
{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

{# --mon-ip is still required, even though we're also putting the Mon IP      #}
{# directly in the placement YAML (see https://tracker.ceph.com/issues/46782) #}
run cephadm bootstrap:
  cmd.run:
    - name: |
        CEPHADM_IMAGE={{ pillar['ceph-salt']['container']['images']['ceph'] }} \
        cephadm --verbose bootstrap \
                --mon-ip {{ pillar['ceph-salt']['bootstrap_mon_ip'] }} \
                --apply-spec {{ bootstrap_spec_yaml_tmpfile }} \
                --config {{ bootstrap_ceph_conf_tmpfile }} \
{%- if not pillar['ceph-salt']['dashboard']['password_update_required'] %}
                --dashboard-password-noupdate \
{%- endif %}
                --initial-dashboard-password {{ dashboard_password }} \
                --initial-dashboard-user {{ dashboard_username }} \
                --output-config /etc/ceph/ceph.conf \
                --output-keyring /etc/ceph/ceph.client.admin.keyring \
{%- if auth %}
                --registry-json /tmp/ceph-salt-registry-json \
{%- endif %}
                --skip-monitoring-stack \
                --skip-prepare-host \
                --skip-pull \
                --ssh-private-key /tmp/ceph-salt-ssh-id_rsa \
                --ssh-public-key /tmp/ceph-salt-ssh-id_rsa.pub \
                --ssh-user {{ ssh_user }} \
{%- for arg, value in pillar['ceph-salt'].get('bootstrap_arguments', {}).items() %}
                --{{ arg }} {{ value if value is not none else '' }} \
{%- endfor %}
                > /var/log/ceph/cephadm.log 2>&1
    - env:
      - NOTIFY_SOCKET: ''
    - creates:
      - /etc/ceph/ceph.conf
      - /etc/ceph/ceph.client.admin.keyring
    - failhard: True

{{ macros.end_step('Run "cephadm bootstrap"') }}

{{ macros.end_stage('Bootstrap the Ceph cluster') }}

{% endif %}
