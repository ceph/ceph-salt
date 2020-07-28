{% import 'macros.yml' as macros %}

{{ macros.begin_stage('Install and configure AppArmor') }}

aa-enabled:
  cmd.run:
    - onfail:
      - test: apparmor
    - failhard: True

aa-teardown:
  cmd.run:
    - onlyif:
      - sh -c "type aa-teardown"
    - failhard: True

stop apparmor:
  service.dead:
    - enable: False
    - failhard: True

uninstall apparmor:
  pkg.removed:
    - pkgs:
      - apparmor
      - apparmor-utils
    - failhard: True

apparmor:
  test.nop

{{ macros.end_stage('Install and configure AppArmor') }}
