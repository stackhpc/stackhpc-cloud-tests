# Copyright (c) 2024 StackHPC Ltd.

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

import os
import pytest


def test_selinux(host):
    """Check that SELinux is enabled and permissive on supported systems."""
    # Adapted from Kayobe host configure tests:
    # https://opendev.org/openstack/kayobe/src/branch/master/playbooks/kayobe-overcloud-host-configure-base/tests/test_overcloud_host_configure.py
    if host.system_info.distribution in {"debian", "ubuntu"}:
        pytest.skip(reason="SELinux is not supported on Debian or Ubuntu")
    # Desired state: enforcing, permissive or disabled
    expected_state = os.environ["SELINUX_STATE"]
    assert expected_state in {"enforcing", "permissive", "disabled"}
    expected_status = "disabled" if expected_state == "disabled" else "enabled"
    expected_mode = expected_state
    selinux = host.check_output("sestatus")
    selinux = selinux.splitlines()
    # Remove duplicate whitespace characters in output
    selinux = [" ".join(x.split()) for x in selinux]

    assert f"SELinux status: {expected_status}" in selinux
    if expected_status == "enabled":
        assert f"Current mode: {expected_mode}" in selinux
        assert f"Mode from config file: {expected_mode}" in selinux
