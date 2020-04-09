{% import 'macros.yml' as macros %}

{% if 'admin' in grains['ceph-salt']['roles'] %}

{% set bootstrap_host = pillar['ceph-salt']['bootstrap_minion'].split('.', 1)[0] %}

{{ macros.begin_stage('Ensure ceph.conf and keyring are present') }}
copy ceph.conf and keyring to other admin nodes:
  cmd.run:
    - name: |
        scp -o "StrictHostKeyChecking=no" -i /tmp/ceph-salt-ssh-id_rsa root@{{ bootstrap_host }}:/etc/ceph/ceph.conf /etc/ceph/
        scp -o "StrictHostKeyChecking=no" -i /tmp/ceph-salt-ssh-id_rsa root@{{ bootstrap_host }}:/etc/ceph/ceph.client.admin.keyring /etc/ceph/
    - failhard: True
{{ macros.end_stage('Ensure ceph.conf and keyring are present') }}

{% endif %}
