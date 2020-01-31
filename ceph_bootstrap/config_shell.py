# pylint: disable=arguments-differ
import logging
import fnmatch


from pyparsing import alphanums, OneOrMore, Optional, Regex, Suppress, Word

import configshell_fb as configshell
from configshell_fb.shell import locatedExpr

from .core import CephNodeManager, SshKeyManager
from .exceptions import CephBootstrapException, PillarFileNotPureYaml
from .salt_utils import PillarManager
from .terminal_utils import PrettyPrinter as PP
from .validate.salt_master import check_salt_master_status, CephSaltPillarNotConfigured


logger = logging.getLogger(__name__)


class OptionHandler:
    def value(self):
        return None, None

    def save(self, value):
        pass

    def reset(self):
        pass

    def read_only(self):
        return False

    def possible_values(self):
        return []

    # pylint: disable=unused-argument
    def children_handler(self, child_name):
        return None

    def commands_map(self):
        return {}


class PillarHandler(OptionHandler):
    def __init__(self, pillar_path):
        self.pillar_path = pillar_path

    def value(self):
        return PillarManager.get(self.pillar_path), None

    def save(self, value):
        PillarManager.set(self.pillar_path, value)

    def reset(self):
        PillarManager.reset(self.pillar_path)

    def read_only(self):
        return False


class RolesGroupHandler(OptionHandler):
    def value(self):
        minions = set()
        idx = 0
        for idx, node in enumerate(CephNodeManager.ceph_salt_nodes().values()):
            if node.roles:
                minions.add(node.minion_id)
        count = len(minions)
        bootstrap_minion = PillarManager.get('ceph-salt:bootstrap_minion')
        return 'Bootstrap minion: {}, Minions w/ roles: {}'.format(bootstrap_minion, count), \
               bootstrap_minion is not None and count == idx + 1


class RoleElementHandler(OptionHandler):
    def __init__(self, ceph_salt_node, role):
        self.ceph_salt_node = ceph_salt_node
        self.role = role

    def value(self):
        if not self.ceph_salt_node.roles - {self.role}:
            return 'no other roles', None
        return "other roles: {}".format(", ".join(self.ceph_salt_node.roles - {self.role})), None


class RoleHandler(OptionHandler):
    def __init__(self, role):
        self.role = role
        self._value = set()

    def _load(self):
        self._value = {n.minion_id for n in CephNodeManager.ceph_salt_nodes().values()
                       if self.role in n.roles}

    def possible_values(self):
        self._load()
        return [n.minion_id for n in CephNodeManager.ceph_salt_nodes().values()]

    def value(self):
        self._load()
        return self._value, True

    def save(self, value):
        self._load()
        _minions = set(value)
        to_remove = self._value - _minions
        to_add = _minions - self._value

        for minion in to_remove:
            CephNodeManager.ceph_salt_nodes()[minion].roles.remove(self.role)
            CephNodeManager.ceph_salt_nodes()[minion].save()

        for minion in to_add:
            CephNodeManager.ceph_salt_nodes()[minion].add_role(self.role)
            CephNodeManager.ceph_salt_nodes()[minion].save()

        CephNodeManager.save_in_pillar()

        self._value = set(value)

    def children_handler(self, child_name):
        return RoleElementHandler(CephNodeManager.ceph_salt_nodes()[child_name], self.role)


class CephSaltNodeHandler(OptionHandler):
    def __init__(self, ceph_salt_node):
        self.ceph_salt_node = ceph_salt_node

    def value(self):
        if not self.ceph_salt_node.roles:
            return 'no roles', False
        return ", ".join(self.ceph_salt_node.roles), None


class CephSaltNodesHandler(OptionHandler):
    def __init__(self):
        self._minions = set()
        self._ceph_salt_nodes = set()

    def value(self):
        self._ceph_salt_nodes = {n.minion_id for n in CephNodeManager.ceph_salt_nodes().values()}
        return self._ceph_salt_nodes, True

    def save(self, value):
        _value = set(value)
        to_remove = self._ceph_salt_nodes - _value
        to_add = _value - self._ceph_salt_nodes

        for minion in to_remove:
            CephNodeManager.remove_node(minion)
        for minion in to_add:
            CephNodeManager.add_node(minion)

        self._ceph_salt_nodes = set(value)

    def possible_values(self):
        if not self._minions:
            self._minions = set(CephNodeManager.list_all_minions())
        return self._minions - self._ceph_salt_nodes

    def children_handler(self, child_name):
        return CephSaltNodeHandler(CephNodeManager.ceph_salt_nodes()[child_name])


class SSHGroupHandler(OptionHandler):
    def commands_map(self):
        return {
            'generate': self.generate_key_pair
        }

    def generate_key_pair(self):
        private_key, public_key = SshKeyManager.generate_key_pair()
        PillarManager.set('ceph-salt:ssh:private_key', private_key)
        PillarManager.set('ceph-salt:ssh:public_key', public_key)
        PP.pl_green('Key pair generated.')

    def value(self):
        stored_priv_key = PillarManager.get('ceph-salt:ssh:private_key')
        stored_pub_key = PillarManager.get('ceph-salt:ssh:public_key')
        if not stored_priv_key and not stored_pub_key:
            return "no key pair set", False
        if not stored_priv_key or not stored_pub_key:
            return "invalid key pair", False
        try:
            SshKeyManager.check_keys(stored_priv_key, stored_pub_key)
            return "Key Pair set", True
        except Exception:  # pylint: disable=broad-except
            return "invalid key pair", False


class SshPrivateKeyHandler(PillarHandler):
    def __init__(self):
        super(SshPrivateKeyHandler, self).__init__('ceph-salt:ssh:private_key')

    def value(self):
        stored_priv_key, _ = super(SshPrivateKeyHandler, self).value()
        stored_pub_key = PillarManager.get('ceph-salt:ssh:public_key')
        try:
            SshKeyManager.check_private_key(stored_priv_key, stored_pub_key)
            return SshKeyManager.key_fingerprint(stored_pub_key), None
        except Exception as ex:  # pylint: disable=broad-except
            return str(ex), False


class SshPublicKeyHandler(PillarHandler):
    def __init__(self):
        super(SshPublicKeyHandler, self).__init__('ceph-salt:ssh:public_key')

    def value(self):
        stored_pub_key, _ = super(SshPublicKeyHandler, self).value()
        stored_priv_key = PillarManager.get('ceph-salt:ssh:private_key')
        try:
            SshKeyManager.check_public_key(stored_priv_key, stored_pub_key)
            return SshKeyManager.key_fingerprint(stored_pub_key), None
        except Exception as ex:  # pylint: disable=broad-except
            return str(ex), False


class TimeServerGroupHandler(OptionHandler):
    def commands_map(self):
        return {
            'enable': self.enable,
            'disable': self.disable
        }

    def enable(self):
        PillarManager.set('ceph-salt:time_server:enabled', True)
        PP.pl_green('Enabled.')

    def disable(self):
        PillarManager.set('ceph-salt:time_server:enabled', False)
        PP.pl_green('Disabled.')

    def value(self):
        val = PillarManager.get('ceph-salt:time_server:enabled')
        if val is None:
            return "enabled", True
        if val:  # enabled
            host = PillarManager.get('ceph-salt:time_server:server_host')
            if host is None:
                return "enabled, no server host set", False

        return ("enabled", True) if val else ("disabled", True)


class TimeServerHandler(PillarHandler):
    def possible_values(self):
        return [n.minion_id for n in CephNodeManager.ceph_salt_nodes().values()]


CEPH_BOOTSTRAP_OPTIONS = {
    'Cluster': {
        'help': '''
                Cluster Options Configuration
                ====================================
                Options to specify the structure of the Ceph cluster, like
                membership, roles, etc...
                ''',
        'options': {
            'Minions': {
                'help': 'The list of salt minions that are used to deploy Ceph',
                'default': [],
                'type': 'minions',
                'handler': CephSaltNodesHandler()
            },
            'Roles': {
                'type': 'group',
                'handler': RolesGroupHandler(),
                'help': '''
                        Roles Configuration
                        ====================================
                        ''',
                'options': {
                    'Mon': {
                        'type': 'minions',
                        'default': [],
                        'handler': RoleHandler('mon'),
                        'help': 'List of minions with Ceph Monitor role'
                    },
                    'Mgr': {
                        'type': 'minions',
                        'default': [],
                        'handler': RoleHandler('mgr'),
                        'help': 'List of minions with Ceph Manager role'
                    },
                }
            },
        }
    },
    'Containers': {
        'help': '''
                Container Options Configuration
                ====================================
                Options to control the configuration of the Ceph containers used
                for deployment.
                ''',
        'options': {
            'Images': {
                'type': 'group',
                'help': "Container images paths",
                'options': {
                    'ceph': {
                        'help': 'Full path of Ceph container image',
                        'default': "docker.io/ceph/daemon-base:latest",
                        'handler': PillarHandler('ceph-salt:container:images:ceph')
                    },
                }
            },
        }
    },
    'Deployment': {
        'help': '''
                Deployment Options Configuration
                =========================================
                Options to control the deployment of Ceph and other services
                ''',
        'options': {
            'Bootstrap': {
                'type': 'flag',
                'help': 'Run "cephadm bootstrap" on one of the Mon machines',
                'handler': PillarHandler('ceph-salt:deploy:bootstrap'),
                'default': True
            },
            'Mon': {
                'type': 'flag',
                'help': 'Deploy all Ceph Monitors',
                'handler': PillarHandler('ceph-salt:deploy:mon'),
                'default': False
            },
            'Mgr': {
                'type': 'flag',
                'help': 'Deploy all Ceph Managers',
                'handler': PillarHandler('ceph-salt:deploy:mgr'),
                'default': False
            },
            'OSD': {
                'type': 'flag',
                'help': 'Deploy all Ceph OSDs',
                'handler': PillarHandler('ceph-salt:deploy:osd'),
                'default': False
            },
            'Dashboard': {
                'type': 'group',
                'help': 'Dashboard settings',
                'options': {
                    'password': {
                        'default': None,
                        'default_text': 'randomly generated',
                        'sensitive': True,
                        'handler': PillarHandler('ceph-salt:dashboard:password')
                    },
                    'username': {
                        'default': 'admin',
                        'handler': PillarHandler('ceph-salt:dashboard:username')
                    }
                }
            }
        }
    },
    'Storage': {
        'help': '''
                Storage Configuration Options
                =====================================
                Options for configuring storage disks used by OSDs
                ''',
        'options': {
            'Drive_Groups': {
                'type': 'list',
                'default': [],
                'help': 'List of drive groups specifications to be used in OSD deployment',
                'handler': PillarHandler('ceph-salt:storage:drive_groups')
            }
        }
    },
    'SSH': {
        'help': '''
                SSH Keys configuration
                ============================
                Options for configuring the SSH keys used by the SSH orchestrator
                ''',
        'handler': SSHGroupHandler(),
        'options': {
            'Private_Key': {
                'default': None,
                'help': "SSH RSA private key",
                'handler': SshPrivateKeyHandler()
            },
            'Public_Key': {
                'default': None,
                'help': "SSH RSA public key",
                'handler': SshPublicKeyHandler()
            },
        }
    },
    'Time_Server': {
        'help': '''
                Time Server Deployment Options
                ==============================
                Options to customize time server deployment and configuration.
                ''',
        'handler': TimeServerGroupHandler(),
        'options': {
            'External_Servers': {
                'type': 'list',
                'default': [],
                'help': 'List of external NTP servers',
                'handler': PillarHandler('ceph-salt:time_server:external_time_servers')
            },
            'Server_Hostname': {
                'default': None,
                'help': 'FQDN of the time server node',
                'handler': TimeServerHandler('ceph-salt:time_server:server_host'),
                'required': True
            },
        }
    },
}


class CephBootstrapRoot(configshell.ConfigNode):
    help_intro = '''
                 ceph-bootstrap Configuration
                 =====================
                 This is a shell where you can manipulate ceph-bootstrap's configuration.
                 Each configuration option is present under a configuration group.
                 You can navigate through the groups and options using the B{ls} and
                 B{cd} commands as in a typical shell.
                 In each path you can type B{help} to see the available commands.
                 Different options might have different commands available.
                 '''

    def __init__(self, shell):
        configshell.ConfigNode.__init__(self, '/', shell=shell)

    def list_commands(self):
        return tuple(['cd', 'ls', 'help', 'exit'])

    def summary(self):
        return "", None


class GroupNode(configshell.ConfigNode):
    def __init__(self, group_name, help, handler, parent):
        configshell.ConfigNode.__init__(self, group_name, parent)
        self.group_name = group_name
        self.help_intro = help
        self.handler = handler

        if self.handler:
            for cmd, func in self.handler.commands_map().items():
                setattr(self, 'ui_command_{}'.format(cmd), func)

    def list_commands(self):
        cmds = ['cd', 'ls', 'help', 'exit', 'reset', 'set']
        if self.handler:
            cmds.extend(list(self.handler.commands_map().keys()))
        return tuple(cmds)

    def summary(self):
        if self.handler:
            return self.handler.value()
        return "", None

    def ui_command_set(self, option_name, value):
        '''
        Sets the value of option
        '''
        self.get_child(option_name).ui_command_set(value)

    def ui_command_reset(self, option_name):
        '''
        Resets option value to the default
        '''
        self.get_child(option_name).ui_command_reset()


class OptionNode(configshell.ConfigNode):
    def __init__(self, option_name, option_dict, parent):
        configshell.ConfigNode.__init__(self, option_name, parent)
        self.option_name = option_name
        self.option_dict = option_dict
        self.help_intro = option_dict.get('help', ' ')
        self.value = None

    def _list_commands(self):
        return []

    def list_commands(self):
        cmds = ['cd', 'ls', 'help', 'exit', 'reset']
        cmds.extend(self._list_commands())
        return tuple(cmds)

    def _find_value(self):
        if self.value is None:
            value = None
            if 'handler' in self.option_dict:
                value, val_type = self.option_dict['handler'].value()
            if value is not None:
                if self.option_dict.get('sensitive', False):
                    return '***', None
                return value, val_type
            if 'default_text' in self.option_dict:
                return self.option_dict['default_text'], None
            if 'default' in self.option_dict:
                return self.option_dict['default'], None
            raise Exception("No default value found for {}".format(self.option_name))
        return self.value, None

    def summary(self):
        value, val_type = self._find_value()
        if isinstance(value, bool):
            value = 'enabled' if value else 'disabled'
        if value is None and self.option_dict.get('required', False):
            return 'not set', False

        value_str = str(value)
        return value_str, val_type

    def ui_command_reset(self):
        '''
        Resets option value to the default
        '''
        if 'handler' in self.option_dict:
            self.option_dict['handler'].reset()
        else:
            self.value = None
        PP.pl_green('Value reset.')

    def _read_only(self):
        if 'handler' in self.option_dict:
            return self.option_dict['handler'].read_only()
        return False


class ValueOptionNode(OptionNode):
    def _list_commands(self):
        return ['set']

    def ui_command_set(self, value):
        '''
        Sets the value of option
        '''
        if self._read_only():
            raise Exception("Option {} cannot be modified".format(self.option_name))
        if 'handler' in self.option_dict:
            self.option_dict['handler'].save(value)
        else:
            self.value = value
        PP.pl_green('Value set.')

    def ui_complete_set(self, parameters, text, current_param):
        matching = []
        for value in self.option_dict['handler'].possible_values():
            if value.startswith(text):
                matching.append(value)
        return matching


class FlagOptionNode(OptionNode):
    def _list_commands(self):
        return ['enable', 'disable']

    def _set_option_value(self, bool_value):
        if self._read_only():
            raise Exception("Option {} cannot be modified".format(self.option_name))
        if 'handler' in self.option_dict:
            self.option_dict['handler'].save(bool_value)
        else:
            self.value = bool_value

    def ui_command_enable(self):
        '''
        Enables the option
        '''
        self._set_option_value(True)
        PP.pl_green('Enabled.')

    def ui_command_disable(self):
        '''
        Disables the option
        '''
        self._set_option_value(False)
        PP.pl_green('Disabled.')


class ListElementNode(configshell.ConfigNode):
    def __init__(self, value, parent):
        configshell.ConfigNode.__init__(self, value, parent)


class ListOptionNode(OptionNode):
    def __init__(self, option_name, option_dict, parent):
        super(ListOptionNode, self).__init__(option_name, option_dict, parent)
        value_list, _ = self._find_value()
        self.value = list(value_list)
        for value in value_list:
            ListElementNode(value, self)

    def _list_commands(self):
        return ['add', 'remove']

    def summary(self):
        value_list, _ = self._find_value()
        return str(len(value_list)) if value_list else 'empty', None

    def ui_command_add(self, value):
        if value not in self.value:
            self.value.append(value)
            self.option_dict['handler'].save(self.value)
            ListElementNode(value, self)
            PP.pl_green('Value added.')
        else:
            PP.pl_red('Value already exists.')

    def ui_command_remove(self, value):
        if value in self.value:
            self.value.remove(value)
            self.option_dict['handler'].save(self.value)
            self.remove_child(self.get_child(value))
            PP.pl_green('Value removed.')
        else:
            PP.pl_red('Value not found.')


class MinionOptionNode(configshell.ConfigNode):
    def __init__(self, minion, handler, parent):
        configshell.ConfigNode.__init__(self, minion, parent)
        self.handler = handler

    def summary(self):
        if self.handler:
            return self.handler.value()
        return "", None


class MinionsOptionNode(OptionNode):
    def __init__(self, option_name, option_dict, parent):
        super(MinionsOptionNode, self).__init__(option_name, option_dict, parent)
        value_list, _ = self._find_value()
        self.value = list(value_list)
        for value in value_list:
            MinionOptionNode(value, option_dict['handler'].children_handler(value), self)

    def _list_commands(self):
        return ['add', 'rm']

    def summary(self):
        value_list, val_type = self._find_value()
        if value_list:
            return "Minions: {}".format(str(len(value_list))), val_type
        return 'no minions', False

    def ui_command_add(self, minion_id):
        matching = fnmatch.filter(self.option_dict['handler'].possible_values(), minion_id)
        counter = 0
        has_errors = False
        for match in matching:
            if match not in self.value:
                new_value = list(self.value)
                new_value.append(match)
                try:
                    self.option_dict['handler'].save(new_value)
                    self.value = new_value
                    MinionOptionNode(match, self.option_dict['handler'].children_handler(match),
                                     self)
                    counter += 1
                except CephBootstrapException as ex:
                    logger.exception(ex)
                    PP.pl_red(ex)
                    has_errors = True
        if counter == 1:
            PP.pl_green('1 minion added.')
        elif counter > 1:
            PP.pl_green('{} minions added.'.format(counter))
        elif not has_errors:
            PP.pl_red('No minions matched "{}".'.format(minion_id))

    def ui_command_rm(self, minion_id):
        matching = fnmatch.filter(self.value, minion_id)
        counter = 0
        has_errors = False
        for match in matching:
            new_value = list(self.value)
            new_value.remove(match)
            try:
                self.option_dict['handler'].save(new_value)
                self.value = new_value
                self.remove_child(self.get_child(match))
                counter += 1
            except CephBootstrapException as ex:
                logger.exception(ex)
                PP.pl_red(ex)
                has_errors = True
        if counter == 1:
            PP.pl_green('1 minion removed.')
        elif counter > 1:
            PP.pl_green('{} minions removed.'.format(counter))
        elif not has_errors:
            PP.pl_red('No minions matched "{}".'.format(minion_id))

    # pylint: disable=unused-argument
    def ui_complete_add(self, parameters, text, current_param):
        matching = []
        for minion in self.option_dict['handler'].possible_values():
            if minion.startswith(text):
                matching.append(minion)
        return matching

    def ui_complete_rm(self, parameters, text, current_param):
        matching = []
        for minion in self.value:
            if minion.startswith(text):
                matching.append(minion)
        return matching


def _generate_option_node(option_name, option_dict, parent):
    if option_dict.get('type', None) == 'group':
        _generate_group_node(option_name, option_dict, parent)
        return

    if 'options' in option_dict:
        raise Exception("Invalid option node {}".format(option_name))

    if option_dict.get('type', None) == 'flag':
        FlagOptionNode(option_name, option_dict, parent)
    elif option_dict.get('type', None) == 'list':
        ListOptionNode(option_name, option_dict, parent)
    elif option_dict.get('type', None) == 'minions':
        MinionsOptionNode(option_name, option_dict, parent)
    else:
        ValueOptionNode(option_name, option_dict, parent)


def _generate_group_node(group_name, group_dict, parent):
    group_node = GroupNode(group_name, group_dict.get('help', ""), group_dict.get('handler', None),
                           parent)
    for option_name, option_dict in group_dict['options'].items():
        _generate_option_node(option_name, option_dict, group_node)


def generate_config_shell_tree(shell):
    root_node = CephBootstrapRoot(shell)
    for group_name, group_dict in CEPH_BOOTSTRAP_OPTIONS.items():
        _generate_group_node(group_name, group_dict, root_node)


class CephBootstrapConfigShell(configshell.ConfigShell):
    # pylint: disable=anomalous-backslash-in-string
    def __init__(self):
        super(CephBootstrapConfigShell, self).__init__(
            '~/.ceph_bootstrap_config_shell')
        # Grammar of the command line
        command = locatedExpr(Word(alphanums + '_'))('command')
        var = Word(alphanums + ';,=_\+/.<>()~@:-%[]*{}" ')  # adding '*'
        value = var
        keyword = Word(alphanums + '_\-')
        kparam = locatedExpr(keyword + Suppress('=') + Optional(value, default=''))('kparams*')
        pparam = locatedExpr(var)('pparams*')
        parameter = kparam | pparam
        parameters = OneOrMore(parameter)
        bookmark = Regex('@([A-Za-z0-9:_.]|-)+')
        pathstd = Regex('([A-Za-z0-9:_.\[\]]|-)*' + '/' + '([A-Za-z0-9:_.\[\]/]|-)*') | '..' | '.'
        path = locatedExpr(bookmark | pathstd | '*')('path')
        parser = Optional(path) + Optional(command) + Optional(parameters)
        self._parser = parser


def check_config_prerequesites():
    try:
        check_salt_master_status()
        return True
    except CephSaltPillarNotConfigured:
        try:
            PillarManager.install_pillar()
            return True
        except PillarFileNotPureYaml:
            PP.println("""
ceph-salt pillar file is not installed yet, and we can't add it automatically
because pillar's top.sls is probably using Jinja2 expressions.
Please create a ceph-salt.sls file in salt's pillar directory with the following
content:

ceph-salt: {}

and add the following pillar configuration to top.sls file:

base:
  'ceph-salt:member':
    - match: grain
    - ceph-salt
""")
    return False


def run_config_shell():
    if not check_config_prerequesites():
        return False
    shell = CephBootstrapConfigShell()
    generate_config_shell_tree(shell)
    while True:
        try:
            shell.run_interactive()
            break
        except CephBootstrapException as ex:
            logger.exception(ex)
            PP.pl_red(ex)
    return True


def run_config_cmdline(cmdline):
    if not check_config_prerequesites():
        return False
    shell = CephBootstrapConfigShell()
    generate_config_shell_tree(shell)
    logger.info("running command: %s", cmdline)
    shell.run_cmdline(cmdline)
    return True
