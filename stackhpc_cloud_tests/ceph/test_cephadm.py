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

"""Checks that the Ceph admin tooling works on this host.

cephadm labels the monitor hosts "_admin", which is what places
/etc/ceph/ceph.conf and the admin keyring on them. Without both of those
no Ceph command can run from the host at all.
"""

import pytest

from stackhpc_cloud_tests.ceph import utils

skip = utils.should_skip("cephadm")

# Distributed by cephadm to hosts labelled "_admin".
CEPH_CONF = "/etc/ceph/ceph.conf"
ADMIN_KEYRING = "/etc/ceph/ceph.client.admin.keyring"


@pytest.mark.skipif(skip, reason="Cephadm tests skipped.")
def test_cephadm_installed(host):
    """Check that the cephadm binary is available."""
    assert host.exists("cephadm")


@pytest.mark.skipif(skip, reason="Cephadm tests skipped.")
def test_cephadm_shell_accessible(host):
    """Check that a cephadm shell starts and can run the Ceph CLI."""
    result = utils.run_ceph(host, "--version")
    message = f"Could not run 'cephadm shell': {result.stderr}"
    assert result.rc == 0, message
    assert "ceph version" in result.stdout


@pytest.mark.skipif(skip, reason="Cephadm tests skipped.")
def test_ceph_conf_present(host):
    """Check that the Ceph configuration file has been distributed."""
    ceph_conf = host.file(CEPH_CONF)
    assert ceph_conf.exists
    # Clients need mon_host to find the cluster.
    assert ceph_conf.contains("mon_host")


@pytest.mark.skipif(skip, reason="Cephadm tests skipped.")
def test_admin_keyring_present(host):
    """Check that the admin keyring exists and only root can read it."""
    keyring = host.file(ADMIN_KEYRING)
    assert keyring.exists

    # File permissions are an octal number. Last digit must be
    # 0 to restrict access to root only
    permission_for_other_users = keyring.mode % 8
    message = f"{ADMIN_KEYRING} can be read by any user on this host"
    assert permission_for_other_users == 0, message


@pytest.mark.skipif(skip, reason="Cephadm tests skipped.")
def test_mon_in_quorum(host):
    """Check that the monitor on this host is a member of the quorum."""
    hostname = host.check_output("hostname -s")
    status = utils.run_ceph_json(host, "-s")
    monitors_in_quorum = status["quorum_names"]

    message = (
        f"The monitor on {hostname} is not in the quorum. "
        f"The quorum contains {monitors_in_quorum}."
    )
    assert hostname in monitors_in_quorum, message
