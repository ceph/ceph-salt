from ..salt_utils import PillarManager


def validate_config(host_ls):
    """
    :return: Error message if config is invalid, otherwise "None"
    """
    bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
    admin_nodes = PillarManager.get('ceph-salt:minions:admin')
    deployed = len(host_ls) > 0
    if not deployed:
        if not bootstrap_minion:
            return "No bootstrap minion specified in config"
        bootstrap_minion_short_name = bootstrap_minion.split('.', 1)[0]
        if bootstrap_minion_short_name not in admin_nodes:
            return "Bootstrap minion must be 'Admin'"
    bootstrap_mon_ip = PillarManager.get('ceph-salt:bootstrap_mon_ip')
    if not bootstrap_mon_ip:
        return "No bootstrap Mon IP specified in config"
    if bootstrap_mon_ip in ['127.0.0.1', '::1']:
        return 'Mon IP cannot be the loopback interface IP'
    all_nodes = PillarManager.get('ceph-salt:minions:all')
    for admin_node in admin_nodes:
        if admin_node not in all_nodes:
            return "One or more Admin nodes are not cluster minions"
    ceph_container_image_path = PillarManager.get('ceph-salt:container:images:ceph')
    if not ceph_container_image_path:
        return "No Ceph container image path specified in config"
    return None
