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

"""Checks that the cluster was configured the way the deployment asked.

CEPH_EXPECTED_POOLS and CEPH_EXPECTED_KEYS hold the cephadm_pools and
cephadm_keys lists as JSON, so the expectations come from the deployment
rather than being repeated here.

Note that Ceph and the cephadm collection both abbreviate capabilities to
"caps" in their data, so that spelling appears when reading their fields.
"""

import pytest

from stackhpc_cloud_tests.ceph import utils

skip = utils.should_skip("ceph-config")


def _applications_by_pool(host):
    """Return a mapping of pool name to the applications using it."""
    return utils.run_ceph_json(host, "osd pool application get")


def _capabilities_by_entity(host):
    """Return a mapping of cephx entity name to its capabilities."""
    # "ceph auth ls" also returns the secret key for every entity. Only the
    # capabilities are kept here so a key cannot reach a test report.
    auth = utils.run_ceph_json(host, "auth ls")

    capabilities_by_entity = {}
    for entry in auth["auth_dump"]:
        capabilities_by_entity[entry["entity"]] = entry["caps"]
    return capabilities_by_entity


@pytest.mark.skipif(skip, reason="Ceph config tests skipped.")
def test_expected_pools_present(subtests, host):
    """Check each pool the deployment asks for exists with its application."""
    expected_pools = utils.json_from_env("CEPH_EXPECTED_POOLS")
    if expected_pools is None:
        pytest.skip("CEPH_EXPECTED_POOLS is not set")

    applications_by_pool = _applications_by_pool(host)

    for pool in expected_pools:
        if pool["state"] != "present":
            continue

        with subtests.test(msg="pool=" + pool["name"]):
            message = f"Pool {pool['name']} does not exist"
            assert pool["name"] in applications_by_pool, message

            # Ceph tags each pool with the application using it, which stops
            # one service writing into another service's pool.
            expected_application = pool.get("application")
            if expected_application is not None:
                applications = applications_by_pool[pool["name"]]
                message = (
                    f"Pool {pool['name']} has applications "
                    f"{list(applications)}, expected {expected_application}"
                )
                assert expected_application in applications, message


@pytest.mark.skipif(skip, reason="Ceph config tests skipped.")
def test_absent_pools_removed(subtests, host):
    """Check that pools the deployment asks to remove are not present."""
    expected_pools = utils.json_from_env("CEPH_EXPECTED_POOLS")
    if expected_pools is None:
        pytest.skip("CEPH_EXPECTED_POOLS is not set")

    applications_by_pool = _applications_by_pool(host)

    for pool in expected_pools:
        if pool["state"] != "absent":
            continue

        with subtests.test(msg="pool=" + pool["name"]):
            message = f"Pool {pool['name']} should have been removed"
            assert pool["name"] not in applications_by_pool, message


@pytest.mark.skipif(skip, reason="Ceph config tests skipped.")
def test_expected_keys_present(subtests, host):
    """Check each cephx key the deployment asks for exists, with its
    capabilities.
    """
    expected_keys = utils.json_from_env("CEPH_EXPECTED_KEYS")
    if expected_keys is None:
        pytest.skip("CEPH_EXPECTED_KEYS is not set")

    capabilities_by_entity = _capabilities_by_entity(host)

    for key in expected_keys:
        if key["state"] != "present":
            continue

        with subtests.test(msg="key=" + key["name"]):
            message = f"Cephx key {key['name']} does not exist"
            assert key["name"] in capabilities_by_entity, message

            # Capabilities decide which pools a client may use, so a wrong
            # one makes a service fail to write with nothing else noticing.
            actual_capabilities = capabilities_by_entity[key["name"]]
            for daemon_type, expected_capability in key["caps"].items():
                actual_capability = actual_capabilities.get(daemon_type)
                message = (
                    f"Cephx key {key['name']} has {daemon_type} capability "
                    f"'{actual_capability}', expected '{expected_capability}'"
                )
                assert actual_capability == expected_capability, message


@pytest.mark.skipif(skip, reason="Ceph config tests skipped.")
def test_absent_keys_removed(subtests, host):
    """Check that cephx keys the deployment asks to remove are not present."""
    expected_keys = utils.json_from_env("CEPH_EXPECTED_KEYS")
    if expected_keys is None:
        pytest.skip("CEPH_EXPECTED_KEYS is not set")

    capabilities_by_entity = _capabilities_by_entity(host)

    for key in expected_keys:
        if key["state"] != "absent":
            continue

        with subtests.test(msg="key=" + key["name"]):
            message = f"Cephx key {key['name']} should have been removed"
            assert key["name"] not in capabilities_by_entity, message
