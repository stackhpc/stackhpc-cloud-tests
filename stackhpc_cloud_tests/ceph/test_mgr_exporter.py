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

"""Checks for the Ceph manager Prometheus exporter.

The exporter is a manager module, so it is served by whichever manager is
active. The standby managers answer on the same port with an empty body, so
a response alone does not prove metrics are being produced. The check that
Prometheus holds the metrics lives in monitoring/test_prometheus.py, where
all of the managers have already been scraped.

These only run when CEPH_MGR_EXPORTER_ENABLED is true.
"""

import os

import pytest
import requests

from stackhpc_cloud_tests.ceph import utils
from stackhpc_cloud_tests.utils import str_to_bool

exporter_enabled = str_to_bool(os.environ.get("CEPH_MGR_EXPORTER_ENABLED", "false"))
skip = utils.should_skip("ceph-exporter") or not exporter_enabled

# The module's own default, used when the port has not been overridden.
DEFAULT_EXPORTER_PORT = 9283

# A metric the exporter always produces, used to prove it is serving data.
EXPECTED_METRIC = "ceph_health_status"

REQUEST_TIMEOUT_SECONDS = 10


def _exporter_port(host):
    """Return the port the manager Prometheus module listens on."""
    settings = utils.run_ceph_json(host, "config dump")

    for setting in settings:
        if setting["name"] == "mgr/prometheus/server_port":
            return int(setting["value"])

    return DEFAULT_EXPORTER_PORT


def _get_metrics(host):
    """Fetch the exporter's metrics page from this host."""
    port = _exporter_port(host)
    url = f"http://localhost:{port}/metrics"

    try:
        return requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        pytest.fail(f"Could not reach the Ceph mgr exporter at {url}: {exc}")


def _is_active_mgr(host):
    """Return whether the active manager is running on this host."""
    hostname = host.check_output("hostname -s")
    mgr_stat = utils.run_ceph_json(host, "mgr stat")

    # The active manager is named "<hostname>.<random suffix>".
    active_mgr_host = mgr_stat["active_name"].split(".")[0]
    return active_mgr_host == hostname


@pytest.mark.skipif(skip, reason="Ceph mgr exporter tests skipped.")
def test_prometheus_module_enabled(host):
    """Check that the manager Prometheus module is enabled."""
    modules = utils.run_ceph_json(host, "mgr module ls")

    # Without this module the manager serves nothing on the exporter port
    # and Prometheus has no Ceph metrics at all.
    message = (
        f"The prometheus manager module is not enabled. Enabled modules are "
        f"{modules['enabled_modules']}"
    )
    assert "prometheus" in modules["enabled_modules"], message


@pytest.mark.skipif(skip, reason="Ceph mgr exporter tests skipped.")
def test_exporter_responds(host):
    """Check that the exporter answers on this host.

    Every manager answers, including the standbys, so this only shows that
    the port is served and not that metrics are being produced.
    """
    response = _get_metrics(host)

    message = f"The exporter returned status {response.status_code}"
    assert response.status_code == 200, message


@pytest.mark.skipif(skip, reason="Ceph mgr exporter tests skipped.")
def test_active_mgr_serves_ceph_metrics(host):
    """Check that the active manager serves Ceph metrics."""
    if not _is_active_mgr(host):
        pytest.skip("The active manager is not on this host")

    response = _get_metrics(host)

    message = (
        f"The active manager returned {len(response.text)} bytes that do not "
        f"contain {EXPECTED_METRIC}"
    )
    assert EXPECTED_METRIC in response.text, message
