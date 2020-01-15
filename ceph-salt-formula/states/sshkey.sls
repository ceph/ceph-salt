# make sure .ssh is present with the right permissions
/home/root/.ssh:
  file.directory:
    - user: root
    - group: root
    - mode: '0700'
    - makedirs: True

{% if 'mgr' in grains['ceph-salt']['roles'] or grains['id'] == pillar['ceph-salt']['bootstrap_mon'] %}
# private key
/root/.ssh/id_rsa:
  file.managed:
    - user: root
    - group: root
    - mode: '0600'
    - contents_pillar: ceph-salt:ssh:private_key

# public key
/root/.ssh/id_rsa.pub:
  file.managed:
    - user: root
    - group: root
    - mode: '0644'
    - contents_pillar: ceph-salt:ssh:public_key
{% endif %}

# add public key to authorized_keys
install ssh key:
    ssh_auth.present:
      - user: root
      - comment: ssh_orchestrator_key
      - config: /%h/.ssh/authorized_keys
      - name: {{ pillar['ceph-salt']['ssh']['public_key'] }}
