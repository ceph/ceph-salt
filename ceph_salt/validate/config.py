from ..core import SshKeyManager
from ..salt_utils import PillarManager


def validate_config(host_ls):
    """
    :return: Error message if config is invalid, otherwise "None"
    """
    all_minions = PillarManager.get('ceph-salt:minions:all', [])
    bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
    admin_minions = PillarManager.get('ceph-salt:minions:admin', [])
    deployed = len(host_ls) > 0
    if not deployed:
        if not bootstrap_minion:
            return "No bootstrap minion specified in config"
        if bootstrap_minion not in admin_minions:
            return "Bootstrap minion must be 'Admin'"
        dashboard_username = PillarManager.get('ceph-salt:dashboard:username')
        if not dashboard_username:
            return "No dashboard username specified in config"
        dashboard_password = PillarManager.get('ceph-salt:dashboard:password')
        if not dashboard_password:
            return "No dashboard password specified in config"
        dashboard_ssl_certificate = PillarManager.get('ceph-salt:dashboard:ssl_certificate')
        dashboard_ssl_certificate_key = PillarManager.get('ceph-salt:dashboard:ssl_certificate_key')
        if dashboard_ssl_certificate and not dashboard_ssl_certificate_key:
            return "Dashboard SSL certificate provided, but no SSL certificate key specified"
        if not dashboard_ssl_certificate and dashboard_ssl_certificate_key:
            return "Dashboard SSL certificate key provided, but no SSL certificate specified"
        if not isinstance(PillarManager.get('ceph-salt:dashboard:password_update_required'), bool):
            return "'ceph-salt:dashboard:password_update_required' must be of type Boolean"
        bootstrap_mon_ip = PillarManager.get('ceph-salt:bootstrap_mon_ip')
        if not bootstrap_mon_ip:
            return "No bootstrap Mon IP specified in config"
        if bootstrap_mon_ip in ['127.0.0.1', '::1']:
            return 'Mon IP cannot be the loopback interface IP'

    # roles
    cephadm_minions = PillarManager.get('ceph-salt:minions:cephadm', [])
    for cephadm_minion in cephadm_minions:
        if cephadm_minion not in all_minions:
            return "Minion '{}' has 'cephadm' role but is not a cluster "\
                   "minion".format(cephadm_minion)
    for admin_minion in admin_minions:
        if admin_minion not in cephadm_minions:
            return "Minion '{}' has 'admin' role but not 'cephadm' "\
                   "role".format(admin_minion)

    # ssh
    user = PillarManager.get('ceph-salt:ssh:user')
    if not user:
        return "No SSH user specified in config"
    priv_key = PillarManager.get('ceph-salt:ssh:private_key')
    if not priv_key:
        return "No SSH private key specified in config"
    pub_key = PillarManager.get('ceph-salt:ssh:public_key')
    if not pub_key:
        return "No SSH public key specified in config"
    try:
        SshKeyManager.check_keys(priv_key, pub_key)
    except Exception:  # pylint: disable=broad-except
        return "Invalid SSH key pair"

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

    # container
    ceph_container_image_path = PillarManager.get('ceph-salt:container:images:ceph')
    if not ceph_container_image_path:
        return "No Ceph container image path specified in config"
    auth = PillarManager.get('ceph-salt:container:auth')
    if auth:
        username = auth.get('username')
        password = auth.get('password')
        registry = auth.get('registry')
        if username or password or registry:
            if not username or not password or not registry:
                return "Registry auth configuration is incomplete"

    return None
