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

"""Checks for RADOS Gateways, which serve the object store APIs over Ceph.

These only run when CEPH_RGW_ENABLED is true.
"""

import os

import pytest

from stackhpc_cloud_tests.ceph import utils
from stackhpc_cloud_tests.utils import str_to_bool

rgw_enabled = str_to_bool(os.environ.get("CEPH_RGW_ENABLED", "false"))
skip = utils.should_skip("ceph-rgw") or not rgw_enabled


def _rgw_services(host):
    """Return the orchestrator services of type rgw."""
    services = utils.run_ceph_json(host, "orch ls")

    rgw_services = []
    for service in services:
        if service["service_type"] == "rgw":
            rgw_services.append(service)
    return rgw_services


def _hosts_labelled_rgw(host):
    """Return the names of hosts cephadm has labelled for running an RGW."""
    cluster_hosts = utils.run_ceph_json(host, "orch host ls")

    labelled = []
    for cluster_host in cluster_hosts:
        if "rgw" in cluster_host["labels"]:
            labelled.append(cluster_host["hostname"])
    return labelled


def _rgw_config(host):
    """Return the client.rgw settings as a mapping of name to value."""
    settings = utils.run_ceph_json(host, "config dump")

    rgw_config = {}
    for setting in settings:
        if setting["section"] == "client.rgw":
            rgw_config[setting["name"]] = setting["value"]
    return rgw_config


@pytest.mark.skipif(skip, reason="Ceph RGW tests skipped.")
def test_rgw_service_reconciled(subtests, host):
    """Check that an RGW service exists and all of its daemons are running."""
    rgw_services = _rgw_services(host)

    # The general reconciliation check passes if no RGW service exists at
    # all, so assert here that object storage was actually deployed.
    assert rgw_services != [], "No RGW service is deployed"

    for service in rgw_services:
        with subtests.test(msg="service=" + service["service_name"]):
            service_status = service["status"]
            daemons_wanted = service_status["size"]
            daemons_running = service_status["running"]

            message = (
                f"{service['service_name']} has {daemons_running} of "
                f"{daemons_wanted} daemons running"
            )
            assert daemons_running == daemons_wanted, message


@pytest.mark.skipif(skip, reason="Ceph RGW tests skipped.")
def test_rgw_hosts_labelled(host):
    """Check that hosts are labelled for running an RGW.

    Placement is driven by the label, so a host that is missing it silently
    gets no RGW daemon.
    """
    labelled_hosts = _hosts_labelled_rgw(host)

    assert labelled_hosts != [], "No host carries the rgw label"

    expected_rgws = utils.count_from_env("CEPH_RGW_COUNT")
    if expected_rgws is not None:
        message = (
            f"Expected {expected_rgws} hosts labelled rgw, "
            f"found {len(labelled_hosts)}: {labelled_hosts}"
        )
        assert len(labelled_hosts) == expected_rgws, message


@pytest.mark.skipif(skip, reason="Ceph RGW tests skipped.")
def test_rgw_daemons_on_labelled_hosts(host):
    """Check that every host labelled for an RGW is actually running one."""
    labelled_hosts = _hosts_labelled_rgw(host)
    daemons = utils.run_ceph_json(host, "orch ps")

    hosts_running_rgw = []
    for daemon in daemons:
        if daemon["daemon_type"] == "rgw":
            hosts_running_rgw.append(daemon["hostname"])

    for hostname in labelled_hosts:
        message = f"Host {hostname} is labelled rgw but runs no RGW daemon"
        assert hostname in hosts_running_rgw, message


@pytest.mark.skipif(skip, reason="Ceph RGW tests skipped.")
def test_rgw_keystone_configured(host):
    """Check that the RGWs are configured to authenticate against Keystone.

    The values themselves are deployment specific, so this checks that
    Keystone authentication and both object storage APIs were set up.
    """
    rgw_config = _rgw_config(host)

    keystone_url = rgw_config.get("rgw_keystone_url")
    message = "rgw_keystone_url is not set, so RGW cannot authenticate users"
    assert keystone_url, message

    s3_uses_keystone = rgw_config.get("rgw_s3_auth_use_keystone")
    message = f"rgw_s3_auth_use_keystone is {s3_uses_keystone}, expected true"
    assert str_to_bool(s3_uses_keystone or ""), message

    # Ceph serves both APIs from the same daemon, and Kolla registers the
    # Swift endpoint in Keystone, so both need to be enabled.
    enabled_apis = rgw_config.get("rgw_enable_apis", "")
    for api in ["s3", "swift"]:
        message = f"rgw_enable_apis is '{enabled_apis}', which omits {api}"
        assert api in enabled_apis, message
