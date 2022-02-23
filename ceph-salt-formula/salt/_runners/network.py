# -*- coding: utf-8 -*-
# pylint: disable=modernize-parse-error,unused-argument
# pylint: skip-file

"""
Network utilities
"""

from __future__ import absolute_import
from __future__ import print_function
import time
import logging
import operator
import re
# pylint: disable=import-error,3rd-party-module-not-gated
from netaddr import IPNetwork, IPAddress
import ipaddress
import pprint
# pylint: disable=relative-import
# pylint: disable=import-error,3rd-party-module-not-gated,blacklisted-external-import,blacklisted-module
from six.moves import range
# pylint: disable=incompatible-py3-code

log = logging.getLogger(__name__)

try:
    import salt.client
except ImportError:
    log.error('Could not import salt.client')

try:
    import salt.ext.six as six
except ImportError:
    log.error('Could not import salt.ext.six')


def help_():
    """
    Usage
    """
    usage = ('salt-run network.get_cpu_count server=minion\n\n'
             '    Returns the number of cpus for a minion\n'
             '\n\n'
             'salt-run network.ping:\n'
             'salt-run network.ping6:\n'
             'salt-run network.ping ipversion="ipv6":\n'
             'salt-run network.ping exclude=target:\n\n'
             'salt-run network.ping remove=192.168.128.0/24:\n\n'
             '    Summarizes network connectivity between minion interfaces\n'
             '\n\n'
             'salt-run network.jumbo_ping:\n\n'
             '    Summarizes network connectivity between minion interfaces for jumbo packets\n'
             '\n\n'
             'salt-run network.iperf:\n'
             'salt-run network.iperf6:\n'
             'salt-run network.iperf ipversion="ipv6":\n'
             'salt-run network.iperf exclude=target:\n\n'
             'salt-run network.ping remove=192.168.128.0/24:\n\n'
             '    Summarizes bandwidth throughput between minion interfaces\n'
             '\n\n')
    print(usage)
    return ""


def get_cpu_count(server):
    """
    Returns the number of cpus for the server
    """
    local = salt.client.LocalClient()
    result = local.cmd("S@{} or {}".format(server, server),
                       'grains.item', ['num_cpus'], tgt_type="compound")
    cpu_core = list(result.values())[0]['num_cpus']
    return cpu_core


def iperf6(exclude=None, remove=None, output=None, **kwargs):
    """
    """
    return iperf(ipversion='ipv6', exclude=exclude, remove=remove, output=output, **kwargs)


def iperf(ipversion='ipv4', exclude=None, remove=None, output=None, **kwargs):
    """
    iperf server created from the each minions and then clients are created
    base on the server's cpu count and request that number of other minions
    as client to hit the server and report the total bendwidth.

    CLI Example:
    .. code-block:: bash
        sudo salt-run network.iperf

    or you can run it with exclude
    .. code-block:: bash
        sudo salt-run network.iperf exclude="E@host*,host-osd-name*,192.168.1.1"

    To get all host iperf result
        sudo salt-run network.iperf output=full

    """
    exclude_string = exclude_iplist = None
    if exclude:
        exclude_string, exclude_iplist = _exclude_filter(exclude)

    addresses = []
    local = salt.client.LocalClient()

    search = _search_criteria()
    if exclude_string:
        search += " and not ( " + exclude_string + " )"
        log.debug("iperf: search {} ".format(search))

    addresses = local.cmd(search, 'grains.get',
                          [ipversion], tgt_type="compound")

    addresses = _remove_minion_not_found(addresses)
    addresses = _flatten(list(addresses.values()))
    addresses = _remove_minion_exclude(addresses, remove)
    try:
        addresses = [addr for addr in addresses if not ipaddress.ip_address(addr).is_loopback]
        addresses = [addr for addr in addresses if not ipaddress.ip_address(addr).is_link_local]
        if exclude_iplist:
            for ex_ip in exclude_iplist:
                log.debug("iperf: removing {} ip ".format(ex_ip))
                addresses.remove(ex_ip)
    except ValueError:
        log.debug("iperf: remove {} ip doesn't exist".format(ex_ip))
    _create_server(addresses)
    result = _create_client(addresses)

    sort_result = _add_unit(sorted(list(result.items()),
                                   key=operator.itemgetter(1),
                                   reverse=True))
    if output:
        return sort_result
    else:
        return {"Slowest 2 hosts": sort_result[-2:],
                "Fastest 2 hosts": sort_result[:2]}


def _search_criteria():
    """
    Return string of all ceph-salt minions; otherwise, default to '*'
    """
    pillar_util = salt.utils.master.MasterPillarUtil('*', "compound",
                                                 use_cached_grains=True,
                                                 grains_fallback=False,
                                                 opts=__opts__)
    cached = pillar_util.get_minion_pillar()
    search = '*'
    for minion in cached:
        try:
            search = " or ".join(cached[minion]['ceph-salt']['minions']['all'])
            break
        except KeyError:
            pass
    return search

def _add_unit(records):
    """
    Add formatting
    """
    stuff = []
    for host in enumerate(records):
        log.debug("Host {} Speed {}".format(host[1][0], host[1][1]))
        stuff.append([host[1][0], "{} Mbits/sec".format(host[1][1])])
    return stuff


def _create_server(addresses):
    """
    Start iperf server
    """
    start_service = []
    local = salt.client.LocalClient()
    log.debug("network.iperf._create_server: address list {} ".format(addresses))
    for server in addresses:
        cpu_core = get_cpu_count(server)
        log.debug("network.iperf._create_server: server {} cpu count {} "
                  .format(server, cpu_core))
        for count in range(cpu_core):
            log.debug("network.iperf._create_server: server {} count {} port {} "
                      .format(server, count, 5200+count))
            start_service.append(local.cmd("S@{}".format(server),
                                           'multi.iperf_server_cmd',
                                           [count, 5200+count], tgt_type="compound"))


def _create_client(addresses):
    """
    Start iperf client
    """
    results = []
    jid = []
    local = salt.client.LocalClient()
    for server in addresses:
        cpu_core = get_cpu_count(server)
        log.debug("network.iperf._create_client: server {} cpu count {} "
                  .format(server, cpu_core))
        clients = list(addresses)
        clients.remove(server)
        clients_size = len(clients)
        # pylint: disable=invalid-name
        for x in range(0, cpu_core, clients_size):
            # pylint: disable=invalid-name
            for y, client in enumerate(clients):
                log.debug("network.iperf._create_client:")
                log.debug("server port:{}, x:{} client:{} to server:{}"
                          .format(5200+x+y, x/clients_size, client, server))
                if x+y < cpu_core:
                    jid.append(
                        local.cmd_async(
                            "S@"+client,
                            'multi.iperf',
                            [server, x/clients_size, 5200+x+y],
                            tgt_type="compound"))
                    log.debug("network.iperf._create_client:")
                    log.debug("calling from client:{} ".format(client))
                    log.debug("to server:{} ".format(server))
                    log.debug("cpu:{} port:{}".format(x/clients_size, 5200+x+y))
        log.debug("network.iperf._create_client:")
        log.debug("Server {} iperf client count {}".format(server, len(jid)))
        time.sleep(8)

    log.debug("iperf: All Async iperf client count {}".format(len(jid)))
    not_done = True
    while not_done:
        not_done = False
        for job in jid:
            if not __salt__['jobs.lookup_jid'](job):
                log.debug("iperf: job not done {} ".format(job))
                time.sleep(1)
                not_done = True
    results = []
    for job in jid:
        result = __salt__['jobs.lookup_jid'](job)
        results.append(result)
    return _summarize_iperf(results)


def jumbo_ping(cluster=None, exclude=None, remove=None, **kwargs):
    """
    Ping with larger packets
    """
    ping(cluster, exclude, ping_type="jumbo")

def ping6(exclude=None, remove=None, ping_type=None, **kwargs):
    """
    Ping IPv6
    """
    return ping(ipversion='ipv6', exclude=exclude, remove=remove, ping_type=ping_type, **kwargs)


def ping(ipversion='ipv4', exclude=None, remove=None, ping_type=None, **kwargs):
    """
    Ping all addresses from all addresses on all minions.  If cluster is passed,
    restrict addresses to public and cluster networks.

    Note: Some optimizations could be done here in the multi module (such as
    skipping the source and destination when they are the same).  However, the
    unoptimized version is taking ~2.5 seconds on 18 minions with 72 addresses
    for success.  Failures take between 6 to 12 seconds.  Optimizations should
    focus there.

    CLI Example:
    .. code-block:: bash
        sudo salt-run network.ping

    or you can run it with exclude
    .. code-block:: bash
        sudo salt-run network.ping exclude="E@host*,host-osd-name*,192.168.1.1"

    or you can run exclude, with remove that host has multiple ip per node
    .. code-block:: bash
        sudo salt-run network.ping exclude="E@host*" remove="192.168.128.0/24,192.168.228.0/24"

    """
    exclude_string = exclude_iplist = None
    if exclude:
        exclude_string, exclude_iplist = _exclude_filter(exclude)

    extra_kwargs = _skip_dunder(kwargs)
    if _skip_dunder(kwargs):
        print("Unsupported parameters:{}".format(" ,".join(list(extra_kwargs.keys()))))
        text = re.sub(re.compile("^ {12}", re.MULTILINE), "", '''
            salt-run network.ping [cluster] [exclude]

            Ping all addresses from all addresses on all minions.
            If exclude is specified, remove matching addresses.
            Detail read the Salt compound matchers.
            All the excluded individual ip address interface will be removed,
            instead of ping from, the ping to interface will be removed.


            Examples:
                salt-run network.ping
                salt-run network.ping6
                salt-run network.ping exclude=L@mon1.ceph
                salt-run network.ping exclude=S@192.168.21.254
                salt-run network.ping exclude=S@192.168.21.0/29
                salt-run network.ping exclude="E@host*,host-osd-name*,192.168.1.1"
                salt-run network.ping remove="192.168.128.0/24"
        ''')
        print(text)
        return ""

    local = salt.client.LocalClient()
    # pylint: disable=redefined-variable-type
    search = _search_criteria()

    if exclude_string:
        search += " and not ( " + exclude_string + " )"
        log.debug("ping: search {} ".format(search))
    addresses = local.cmd(search, 'grains.get',
                          [ipversion], tgt_type="compound")
    addresses = _remove_minion_not_found(addresses)
    addresses = _flatten(list(addresses.values()))
    addresses = _remove_minion_exclude(addresses, remove)
    try:
        addresses = [addr for addr in addresses if not ipaddress.ip_address(addr).is_loopback]
        addresses = [addr for addr in addresses if not ipaddress.ip_address(addr).is_link_local]
        log.info("addresses:\n{}".format(pprint.pformat(addresses)))
        if exclude_iplist:
            for ex_ip in exclude_iplist:
                log.debug("ping: removing {} ip ".format(ex_ip))
                addresses.remove(ex_ip)
    except ValueError:
        log.debug("ping: remove {} ip doesn't exist".format(ex_ip))

    if ping_type == "jumbo":
        results = local.cmd(search, 'multi.jumbo_ping',
                            addresses, tgt_type="compound")
    else:
        results = local.cmd(search, 'multi.ping',
                            addresses, tgt_type="compound")
    #results = _remove_minion_not_found(results)
    _summarize(len(addresses), results)
    return ""


def _ipversion(_network):
    """
    Return the address version
    """
    try:
        network = ipaddress.ip_network(u'{}'.format(_network))
    except ValueError as err:
        log.error("Invalid network {}".format(err))
        return 'ipv4'
    if network.version == 6:
        return 'ipv6'
    return 'ipv4'


def _address(addresses, network):
    """
    Return all addresses in the given network

    Note: list comprehension vs. netaddr vs. simple
    """
    matched = []
    for address in addresses:
        log.debug("_address: ip {} in network {} ".format(address, network))
        if IPAddress(address) in IPNetwork(network):
            matched.append(address)
    return matched


def _remove_minion_exclude(addresses, remove_subnet_list):
    """
    Some minion has multiple interface and address remove those address
    may not be needed in the result but included in the minion list
    e.g. minion has interface eth0 192.168.128.101 and 192.168.228.101 both
    ip, which you want to remove 192.168.228.0/24 subnet address
    """
    pattern_ipcidr = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}" +
        r"([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])" +
        r"(\/([0-9]|[1-2][0-9]|3[0-2]))$")
    log.debug("_remove_minion_exclude: removing {} ".format(remove_subnet_list))
    if remove_subnet_list:
        remove_subnets = remove_subnet_list.split(",")
    else:
        remove_subnets = []
    remove_list = []
    for subnet in remove_subnets:
        if pattern_ipcidr.match(subnet):
            log.debug("remove subnet {} in address {}".format(subnet, addresses))
            for addr in addresses:
                log.debug("look address {} in {}".format(addr, subnet))
                if IPAddress(addr) in IPNetwork(subnet):
                    log.debug("remove address {} ".format(addr))
                    remove_list.append(addr)
    new_list = [ip for ip in addresses if ip not in remove_list]
    log.debug("_remove_minion_exclude: new_list {}".format(new_list))
    return new_list


def _remove_minion_not_found(addresses):
    """
    Return all the correct value instead of not found values
    """
    remove_addrs = set()
    for k in addresses:
        if not isinstance(addresses[k], list):
            log.warning("Removing {}: returned {}".format(k, addresses[k]))
            remove_addrs.add(k)
    for k in remove_addrs:
        del addresses[k]
    log.debug("_remove_minion_not_found: after {}".format(addresses))
    return addresses


def _exclude_filter(excluded):
    """
    Internal exclude_filter return string in compound format

    Compound format = {'G': 'grain', 'P': 'grain_pcre', 'I': 'pillar',
                       'J': 'pillar_pcre', 'L': 'list', 'N': None,
                       'S': 'ipcidr', 'E': 'pcre'}
    IPV4 address = "255.255.255.255"
    hostname = "myhostname"
    """

    log.debug("_exclude_filter: excluding {}".format(excluded))
    excluded = excluded.split(",")
    log.debug("_exclude_filter: split ',' {}".format(excluded))

    pattern_compound = re.compile(r"^.*([GPIJLNSE]\@).*$")
    pattern_iplist = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}" +
        r"([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$")
    pattern_ipcidr = re.compile(
        r"^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}" +
        r"([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])" +
        r"(\/([0-9]|[1-2][0-9]|3[0-2]))$")
    pattern_hostlist = re.compile(
        r"^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9-]*[a-zA-Z0-9]).)*" +
        r"([A-Za-z]|[A-Za-z][A-Za-z0-9-]*[A-Za-z0-9])$")
    compound = []
    ipcidr = []
    iplist = []
    hostlist = []
    regex_list = []
    for para in excluded:
        if pattern_compound.match(para):
            log.debug("_exclude_filter: Compound {}".format(para))
            compound.append(para)
        elif pattern_iplist.match(para):
            log.debug("_exclude_filter: ip {}".format(para))
            iplist.append(para)
        elif pattern_ipcidr.match(para):
            log.debug("_exclude_filter: ipcidr {}".format(para))
            ipcidr.append("S@"+para)
        elif pattern_hostlist.match(para):
            hostlist.append("L@"+para)
            log.debug("_exclude_filter: hostname {}".format(para))
        else:
            regex_list.append("E@"+para)
            log.debug("_exclude_filter: Regex host? {}".format(para))

    # if ipcidr:
    #    log.debug("_exclude_filter ip subnet not working = {}".format(ipcidr))
    new_compound_excluded = " or ".join(
        compound + hostlist + regex_list + ipcidr)
    log.debug("{}".format(new_compound_excluded))
    log.debug("{}".format(new_compound_excluded))
    if new_compound_excluded and iplist:
        return new_compound_excluded, iplist
    elif new_compound_excluded:
        return new_compound_excluded, None
    elif iplist:
        return None, iplist
    return None, None


def _flatten(_list):
    """
    Flatten a array of arrays
    """
    log.debug("_flatten: {}".format(_list))
    return list(set(item for sublist in _list for item in sublist))


def _summarize(total, results):
    """
    Summarize the successes, failures and errors across all minions
    """
    success = []
    failed = []
    errored = []
    slow = []
    log.debug("_summarize: results {}".format(results))
    for host in sorted(six.iterkeys(results)):
        if results[host]['succeeded'] == total:
            success.append(host)
        if 'failed' in results[host]:
            failed.append("{} from {}".format(results[host]['failed'], host))
        if 'errored' in results[host]:
            errored.append("{} from {}".format(results[host]['errored'], host))
        if 'slow' in results[host]:
            slow.append("{} from {} average rtt {}".format(
                results[host]['slow'], host,
                "{0:.2f}".format(results[host]['avg'])))

    if success:
        avg = sum(results[host].get('avg') for host in results) / len(results)
    else:
        avg = 0

    print("Succeeded: {} addresses from {} minions average rtt {} ms".format(
        total, len(success), "{0:.2f}".format(avg)))
    if slow:
        print("Warning: \n    {}".format("\n    ".join(slow)))
    if failed:
        print("Failed: \n    {}".format("\n    ".join(failed)))
    if errored:
        print("Errored: \n    {}".format("\n    ".join(errored)))


def _iperf_result_get_server(result):
    """
    Return server results
    """
    return result['server']


def _summarize_iperf(results):
    """
    iperf summarize the successes, failures and errors across all minions
    """
    server_results = {}
    log.debug("Results {} ".format(results))
    for result in results:
        for host in result:
            log.debug("Server {}".format(result[host]['server']))
            if not result[host]['server'] in server_results:
                server_results.update({result[host]['server']: ""})
            if result[host]['succeeded']:
                log.debug("filter:\n{}".format(result[host]['filter']))
                server_results[result[host]['server']] += " " + result[host]['filter']
                log.debug("Speed {}".format(server_results[result[host]['server']]))
            elif result[host]['failed']:
                log.warning("{} failed to connect to {}".format(host, result[host]['server']))
            elif result[host]['errored']:
                log.warning("iperf errored on {}".format(host))

    for key, result in six.iteritems(server_results):
        total = 0
        speed = result.split('Mbits/sec')
        speed = [_f for _f in speed if _f]
        try:
            for value in speed:
                total += float(value.strip())
            # server_results[key] = str(total) + " Mbits/sec"
            server_results[key] = int(total)
        except ValueError:
            continue
    return server_results


def _skip_dunder(settings):
    """
    Skip double underscore keys
    """
    return {k: v for k, v in six.iteritems(settings) if not k.startswith('__')}


__func_alias__ = {
                 'help_': 'help',
            }
