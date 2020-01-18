# This file is part of the ceph-bootstrap integration test suite

set -e

#
# helper functions (not to be called directly from test scripts)
#

function _ceph_cluster_running {
    set -x
    ceph status
    set +x
}

function _copy_file_from_minion_to_master {
    local MINION="$1"
    local FULL_PATH="$2"
    salt --static --out json "$MINION" cmd.shell "cat $FULL_PATH" | jq -r \.\"$MINION\" > $FULL_PATH
}

function _first_x_node {
    local ROLE=$1
    salt --static --out json -G "ceph-salt:roles:$ROLE" test.true 2>/dev/null | jq -r 'keys[0]'
}

function _grace_period {
    local SECONDS=$1
    echo "${SECONDS}-second grace period"
    sleep $SECONDS
}

function _ping_minions_until_all_respond {
    local RESPONDING=""
    for i in {1..20} ; do
        sleep 10
        RESPONDING=$(salt '*' test.ping 2>/dev/null | grep True 2>/dev/null | wc --lines)
        echo "Of $TOTAL_NODES total minions, $RESPONDING are responding"
        test "$TOTAL_NODES" -eq "$RESPONDING" && break
    done
}

