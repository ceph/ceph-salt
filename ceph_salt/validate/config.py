from ..salt_utils import PillarManager


def validate_config():
    """
    :return: Error message if config is invalid, otherwise "None"
    """
    bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
    if not bootstrap_minion:
        return "At least one minion must be both 'Mgr' and 'Mon'"
    bootstrap_minion_short_name = bootstrap_minion.split('.', 1)[0]
    admin_nodes = PillarManager.get('ceph-salt:minions:admin')
    if bootstrap_minion_short_name not in admin_nodes:
        return "Bootstrap minion must be 'Admin'"
    ceph_container_image_path = PillarManager.get('ceph-salt:container:images:ceph')
    if not ceph_container_image_path:
        return "No Ceph container image path specified in config"
    return None
