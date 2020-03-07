from ..salt_utils import PillarManager


def validate_config():
    """
    :return: Error message if config is invalid, otherwise "None"
    """
    bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
    if not bootstrap_minion:
        return "At least one minion must be both 'Mgr' and 'Mon'"
    ceph_container_image_path = PillarManager.get('ceph-salt:container:images:ceph')
    if not ceph_container_image_path:
        return "No Ceph container image path specified in config"
    return None
