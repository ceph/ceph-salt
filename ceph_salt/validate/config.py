from ..salt_utils import PillarManager


def validate_config(host_ls):
    """
    :return: Error message if config is invalid, otherwise "None"
    """
    all_minions = PillarManager.get('ceph-salt:minions:all')
    bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
    admin_minions = PillarManager.get('ceph-salt:minions:admin')
    deployed = len(host_ls) > 0
    if not deployed:
        if not bootstrap_minion:
            return "No bootstrap minion specified in config"
        if bootstrap_minion not in admin_minions:
            return "Bootstrap minion must be 'Admin'"
        dashboard_username = PillarManager.get('ceph-salt:dashboard:username')
        if not dashboard_username:
            return "No dashboard username specified in config"
        bootstrap_mon_ip = PillarManager.get('ceph-salt:bootstrap_mon_ip')
        if not bootstrap_mon_ip:
            return "No bootstrap Mon IP specified in config"
        if bootstrap_mon_ip in ['127.0.0.1', '::1']:
            return 'Mon IP cannot be the loopback interface IP'

    # system_update
    if not isinstance(PillarManager.get('ceph-salt:updates:enabled'), bool):
        return "'ceph-salt:updates:enabled' must be of type Boolean"
    if not isinstance(PillarManager.get('ceph-salt:updates:reboot'), bool):
        return "'ceph-salt:updates:reboot' must be of type Boolean"

    # time_server
    time_server_enabled = PillarManager.get('ceph-salt:time_server:enabled')
    if not isinstance(time_server_enabled, bool):
        return "'ceph-salt:time_server:enabled' must be of type Boolean"
    if time_server_enabled:
        time_server_host = PillarManager.get('ceph-salt:time_server:server_host')
        if not time_server_host:
            return 'No time server host specified in config'
        time_server_is_minion = time_server_host in all_minions
        time_server_subnet = PillarManager.get('ceph-salt:time_server:subnet')
        not_minion_err = ('Time server is not a minion: {} '
                          'setting will not have any effect')
        if time_server_is_minion and not time_server_subnet:
            return 'No time server subnet specified in config'
        if not time_server_is_minion and time_server_subnet:
            return not_minion_err.format('time server subnet')
        external_time_servers = PillarManager.get('ceph-salt:time_server:external_time_servers')
        if time_server_is_minion and not external_time_servers:
            return 'No external time servers specified in config'
        if not time_server_is_minion and external_time_servers:
            return not_minion_err.format('external time servers')
    for admin_minion in admin_minions:
        if admin_minion not in all_minions:
            return "One or more Admin nodes are not cluster minions"
    ceph_container_image_path = PillarManager.get('ceph-salt:container:images:ceph')
    if not ceph_container_image_path:
        return "No Ceph container image path specified in config"
    return None
