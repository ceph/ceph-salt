{% set minion_service_file = "/usr/lib/systemd/system/salt-minion.service" %}

{% if salt['file.file_exists'](minion_service_file) %}

# FIXME: work around bsc#1167218 - remove this when that bug is fixed!
work around podman/runc bug, step 1:
  file.line:
    - name: {{ minion_service_file }}
    - match: '^Type=notify'
    - mode: replace
    - content: '#Type=notify'

# FIXME: work around bsc#1167218 - remove this when that bug is fixed!
work around podman/runc bug, step 2:
  file.line:
    - name: {{ minion_service_file }}
    - match: '^NotifyAccess=all'
    - mode: replace
    - content: '#NotifyAccess=all'

# FIXME: work around bsc#1167218 - remove this when that bug is fixed!
restart salt-minion:
  cmd.run:
    - name: 'salt-call service.restart salt-minion'
    - failhard: True

# FIXME: work around bsc#1167218 - remove this when that bug is fixed!
wait for salt-minion:
  loop.until_no_eval:
    - name: saltutil.runner
    - expected:
        - my_minion
    - args:
        - manage.up
    - kwargs:
        tgt: my_minion
    - period: 3
    - init_wait: 3

{% endif %}  # salt['file.file_exists'](minion_service_file)

reset provisioned:
  grains.present:
    - name: ceph-salt:execution:provisioned
    - value: False

reset failure:
  grains.present:
    - name: ceph-salt:execution:failed
    - value: False
