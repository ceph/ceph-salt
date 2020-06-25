remove ceph-salt-ssh-id_rsa:
  file.absent:
    - name: /tmp/ceph-salt-ssh-id_rsa
    - failhard: True

remove ceph-salt-ssh-id_rsa.pub:
  file.absent:
    - name: /tmp/ceph-salt-ssh-id_rsa.pub
    - failhard: True

{% set registries = pillar['ceph-salt'].get('container', {}).get('auth', []) -%}
{%- for reg in registries %}
remove ceph-salt-registry-password-{{loop.index}}:
  file.absent:
    - name: /tmp/ceph-salt-registry-password-{{loop.index}}
    - failhard: True
logout from registry {{loop.index}}:
  cmd.run:
    - name: |
        podman logout {{reg.registry}}
    - failhard: True
{%- endfor %}
