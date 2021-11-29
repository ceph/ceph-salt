{% if 'admin' not in grains['ceph-salt']['roles'] %}

remove ceph-salt-ssh-id_rsa:
  file.absent:
    - name: {{ salt['user.info']('cephadm').home }}/.ssh/id_rsa
    - failhard: True

remove ceph-salt-ssh-id_rsa.pub:
  file.absent:
    - name: {{ salt['user.info']('cephadm').home }}/.ssh/id_rsa.pub
    - failhard: True

{% endif %}
