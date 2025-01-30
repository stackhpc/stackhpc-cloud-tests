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

import json
import os
from packaging.version import parse
import pytest


@pytest.fixture
def docker_info(host, scope="session"):
    """Pytest fixture that provides the output of 'docker info'."""
    with host.sudo("stack"):
        docker_info = host.check_output("docker info --format json")
    return json.loads(docker_info)


def test_docker_version(host):
    """Check that Docker is accessible and optionally check version."""
    # An optional inclusive minimum version.
    min_version = os.environ.get("DOCKER_VERSION_MIN")
    # An optional exclusive maximum version.
    max_version = os.environ.get("DOCKER_VERSION_MAX")
    with host.sudo("stack"):
        client_version = parse(host.docker.client_version())
        server_version = parse(host.docker.server_version())
    if min_version:
        min_version = parse(min_version)
        assert client_version >= min_version
        assert server_version >= min_version
    if max_version:
        max_version = parse(max_version)
        assert client_version < max_version
        assert server_version < max_version


def test_docker_containers(subtests, host):
    """Check that Docker containers are healthy."""
    with host.sudo("stack"):
        docker_containers = host.docker.get_containers()
    for container in docker_containers:
        # Use the subtests fixture to create a dynamically parametrised test
        # based on the containers on the system.
        with subtests.test(msg="container=" + container.name):
            state = container.inspect()["State"]
            assert state["Running"]
            assert not state["Restarting"]
            assert not state["Dead"]
            assert not state["OOMKilled"]
            if "Health" in state:
                assert state["Health"]["Status"] == "healthy"
            if "HostConfig" in state:
                assert state["HostConfig"]["LogConfig"]["Type"] == "json-file"
                assert "max-file" in state["HostConfig"]["LogConfig"]["Config"]
                assert "max-size" in state["HostConfig"]["LogConfig"]["Config"]


def test_docker_driver(docker_info):
    """Check that Docker is using the overlay2 storage driver."""
    assert docker_info["Driver"] == "overlay2"


def test_no_bridge_network_exists(host):
    """Check that no bridge network exists."""
    with host.sudo("stack"):
        docker_networks = host.check_output("docker network ls --format json")
    for network in docker_networks.splitlines():
        network = json.loads(network)
        assert network["Name"] != "bridge"
        assert network["Driver"] != "bridge"


def test_ip_forwarding_disabled(docker_info):
    """Check that IP forwarding is disabled."""
    assert not docker_info["IPv4Forwarding"]


def test_iptables_disabled(docker_info):
    """Check that IPTables manipulation is disabled."""
    assert not docker_info["BridgeNfIptables"]
    assert not docker_info["BridgeNfIp6tables"]


def test_live_restore_enabled(docker_info):
    """Check that live restore is enabled."""
    assert docker_info["LiveRestoreEnabled"]
