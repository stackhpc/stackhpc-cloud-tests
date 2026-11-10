# Copyright (c) 2026 StackHPC Ltd.

# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import pytest

from stackhpc_cloud_tests.ceph import utils

skip = utils.should_skip("ceph-health")


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_health_ok(host):
    """Check that the cluster reports no health warnings or errors."""
    status = utils.run_ceph_json(host, "-s")
    health = status["health"]

    if health["status"] == "HEALTH_OK":
        return

    # Some deployments expect a warning.
    # Those codes can be allowed individually.
    allowed_checks = utils.list_from_env("CEPH_HEALTH_ALLOWED_CHECKS")

    unexpected_checks = []
    for check_code in health["checks"]:
        if check_code not in allowed_checks:
            unexpected_checks.append(check_code)

    message = f"Ceph is {health['status']} with checks {unexpected_checks}"
    assert unexpected_checks == [], message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_mon_quorum(host):
    """Check that every monitor the cluster knows about is in the quorum."""
    status = utils.run_ceph_json(host, "-s")
    monitors_in_quorum = status["quorum_names"]
    monitors_known = status["monmap"]["num_mons"]

    message = (
        f"Only {len(monitors_in_quorum)} of {monitors_known} monitors are in "
        f"the quorum: {monitors_in_quorum}"
    )
    assert len(monitors_in_quorum) == monitors_known, message

    # A monitor that was never deployed is invisible to the check above,
    # because the remaining monitors still form a healthy quorum.
    expected_monitors = utils.count_from_env("CEPH_MON_COUNT")
    if expected_monitors is not None:
        message = (
            f"Expected {expected_monitors} monitors, the cluster knows "
            f"about {monitors_known}"
        )
        assert monitors_known == expected_monitors, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_mgr_available(host):
    """Check that a manager is active and that the standbys are present."""
    status = utils.run_ceph_json(host, "-s")
    mgrmap = status["mgrmap"]

    assert mgrmap["available"], "No Ceph manager is active"

    # One manager is active and the rest are standbys.
    expected_managers = utils.count_from_env("CEPH_MGR_COUNT")
    if expected_managers is not None:
        managers_running = 1 + mgrmap["num_standbys"]
        message = f"Expected {expected_managers} managers, found {managers_running}"
        assert managers_running == expected_managers, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_osds_up_and_in(host):
    """Check that every OSD is running and accepting data."""
    status = utils.run_ceph_json(host, "-s")
    osdmap = status["osdmap"]
    total_osds = osdmap["num_osds"]

    # "up" means the OSD process is running, "in" means it is accepting
    # data. An OSD can be up but out, for example while being drained.
    message = f"Only {osdmap['num_up_osds']} of {total_osds} OSDs are up"
    assert osdmap["num_up_osds"] == total_osds, message

    message = f"Only {osdmap['num_in_osds']} of {total_osds} OSDs are in"
    assert osdmap["num_in_osds"] == total_osds, message

    expected_osds = utils.count_from_env("CEPH_OSD_COUNT")
    if expected_osds is not None:
        message = f"Expected {expected_osds} OSDs, the cluster has {total_osds}"
        assert total_osds == expected_osds, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_pgs_active_clean(subtests, host):
    """Check that every placement group is active and clean."""
    status = utils.run_ceph_json(host, "-s")

    for pg_state in status["pgmap"]["pgs_by_state"]:
        state_name = pg_state["state_name"]
        with subtests.test(msg="state=" + state_name):
            # State names are joined with "+", such as "active+clean" or
            # "active+clean+scrubbing+deep". Check for
            # the two main states we need only
            states = state_name.split("+")
            message = f"{pg_state['count']} placement groups are {state_name}"
            assert "active" in states, message
            assert "clean" in states, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_no_remapped_pgs(host):
    """Check that no placement groups are waiting to move between OSDs."""
    status = utils.run_ceph_json(host, "-s")
    remapped_pgs = status["osdmap"]["num_remapped_pgs"]

    message = f"{remapped_pgs} placement groups are remapped"
    assert remapped_pgs == 0, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_orch_services_reconciled(subtests, host):
    """Check that cephadm has started as many daemons as each service wants."""
    services = utils.run_ceph_json(host, "orch ls")

    for service in services:
        service_status = service["status"]
        daemons_wanted = service_status.get("size")
        daemons_running = service_status.get("running")

        # Services that cephadm does not manage do not report a size.
        if daemons_wanted is None:
            continue

        with subtests.test(msg="service=" + service["service_name"]):
            message = (
                f"{service['service_name']} has {daemons_running} of "
                f"{daemons_wanted} daemons running"
            )
            assert daemons_running == daemons_wanted, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_orch_daemons_running(subtests, host):
    """Check that every individual daemon cephadm deployed is running."""
    daemons = utils.run_ceph_json(host, "orch ps")

    # Without this an empty list would pass every check below.
    assert daemons != [], "cephadm reports no daemons at all"

    for daemon in daemons:
        with subtests.test(msg="daemon=" + daemon["daemon_name"]):
            # "status" is a numeric code and "status_desc" is the same thing
            # as a word, which reads better in a failure message.
            message = (
                f"{daemon['daemon_name']} on {daemon['hostname']} is "
                f"{daemon['status_desc']}"
            )
            assert daemon["status_desc"] == "running", message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_versions_consistent(subtests, host):
    """Check that all daemons of each type run the same Ceph version."""
    versions = utils.run_ceph_json(host, "versions")

    for daemon_type, counts_by_version in versions.items():
        with subtests.test(msg="daemon=" + daemon_type):
            message = (
                f"{daemon_type} daemons run mixed versions: {counts_by_version}"
            )
            assert len(counts_by_version) == 1, message


@pytest.mark.skipif(skip, reason="Ceph health tests skipped.")
def test_no_crashes(host):
    """Check that no daemon has recorded a crash."""
    crashes = utils.run_ceph_json(host, "crash ls")

    message = f"Ceph has recorded {len(crashes)} crashes: {crashes}"
    assert crashes == [], message
