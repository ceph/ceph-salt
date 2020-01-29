#
# This file is part of the ceph-bootstrap integration test suite.
# It contains various cluster introspection functions.
#

set -e

function json_total_nodes {
    salt --static --out json '*' test.ping 2>/dev/null | jq '. | length'
}

function json_osd_nodes {
    ceph osd tree -f json-pretty | \
        jq '[.nodes[] | select(.type == "host")] | length'
}

function json_total_mgrs {
    echo "$(($(ceph status --format json | jq -r .mgrmap.num_standbys) + 1))"
}

function json_total_mons {
    ceph status --format json | jq -r .monmap.num_mons
}

function json_total_osds {
    ceph osd ls --format json | jq '. | length'
}
