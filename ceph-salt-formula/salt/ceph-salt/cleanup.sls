remove ceph-salt-ssh-id_rsa:
  file.absent:
    - name: /tmp/ceph-salt-ssh-id_rsa
    - failhard: True

remove ceph-salt-ssh-id_rsa.pub:
  file.absent:
    - name: /tmp/ceph-salt-ssh-id_rsa.pub
    - failhard: True

remove ceph-salt-registry-password:
  file.absent:
    - name: /tmp/ceph-salt-registry-password
    - failhard: True

{% set auth = pillar['ceph-salt'].get('container', {}).get('auth', {}) %}

{% if auth %}

logout from registry:
  cmd.run:
    - name: |
        podman logout {{ auth.get('registry') }}
    - failhard: True

{% endif %}
