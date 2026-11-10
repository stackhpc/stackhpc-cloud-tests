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
from prometheus_api_client import PrometheusConnect
import pytest

from stackhpc_cloud_tests import utils

skip = False
if os.environ.get("SKIP_SCT") is not None:
    skip_sct = os.environ.get("SKIP_SCT")
    if "prometheus" in skip_sct:
        skip = True

# The Ceph metrics that the alert rules in
# etc/kayobe/kolla/config/prometheus/ceph.rules depend on. If the exporter
# stops producing them, we would ideally like to catch that in CI
CEPH_MGR_EXPORTER_METRICS = [
    "ceph_health_status",
    "ceph_mon_quorum_status",
    "ceph_osd_up",
    "ceph_pg_total",
    "ceph_pool_metadata",
]

@pytest.fixture
def prom() -> PrometheusConnect:
    """Pytest fixture that creates a Prometheus API client."""
    # https://github.com/4n4nd/prometheus-api-client-python/
    prometheus_url = os.environ["PROMETHEUS_URL"]
    kwargs = {}
    if "PROMETHEUS_USERNAME" in os.environ:
        prometheus_username = os.environ["PROMETHEUS_USERNAME"]
        prometheus_password = os.environ["PROMETHEUS_PASSWORD"]
        kwargs["auth"] = (prometheus_username, prometheus_password)
    return PrometheusConnect(url=prometheus_url, disable_ssl=True, **kwargs)

@pytest.mark.skipif(skip, reason="Prometheus tests skipped.")
def test_prometheus_connection(prom):
    """Check that Prometheus is accessible."""
    assert prom.check_prometheus_connection()

@pytest.mark.skipif(skip, reason="Prometheus tests skipped.")
def test_prometheus_node_exporter_metrics(prom):
    """Check that expected node exporter metrics exist."""
    metrics = prom.all_metrics()
    assert "node_cpu_seconds_total" in metrics

@pytest.mark.skipif(skip, reason="Prometheus tests skipped.")
def test_prometheus_ceph_mgr_exporter_metrics(prom):
    """Check that Prometheus has scraped the Ceph manager exporter."""
    if not utils.str_to_bool(os.environ.get("CEPH_MGR_EXPORTER_ENABLED", "false")):
        pytest.skip("The Ceph mgr exporter is not enabled")

    metrics = prom.all_metrics()

    for metric in CEPH_MGR_EXPORTER_METRICS:
        message = f"Prometheus has no {metric} metric from the Ceph mgr exporter"
        assert metric in metrics, message

@pytest.mark.skipif(skip, reason="Prometheus tests skipped.")
def test_prometheus_ceph_rgw_probes_succeed(prom):
    """Check that the blackbox probes against the RGW endpoints succeed."""
    if not utils.str_to_bool(os.environ.get("CEPH_RGW_ENABLED", "false")):
        pytest.skip("Ceph RGW is not enabled")

    # Kayobe labels each blackbox target with a service name taken from the
    # target string, giving service="ceph_rgw" for the public endpoint and
    # service="ceph_rgw_internal" for the internal one.
    probes = prom.custom_query('probe_success{service=~"ceph_rgw.*"}')

    assert probes, "Prometheus has no blackbox probes for the RGW endpoints"

    for probe in probes:
        service = probe["metric"]["service"]
        instance = probe["metric"]["instance"]
        succeeded = float(probe["value"][1])

        message = f"Blackbox probe {service} against {instance} is failing"
        assert succeeded == 1, message

@pytest.mark.skipif(skip, reason="Prometheus tests skipped.")
def test_prometheus_alerts_inactive(prom):
    """Check that no Prometheus alerts are active."""
    # https://prometheus.io/docs/prometheus/latest/querying/api/#alerts
    response = prom._session.get(
        "{0}/api/v1/alerts".format(prom.url),
        verify=prom._session.verify,
        headers=prom.headers,
        auth=prom.auth,
        cert=prom._session.cert,
    )
    assert response.ok
    response = response.json()
    assert "status" in response
    assert response["status"] == "success"
    assert "data" in response
    alerts = response["data"]["alerts"] or []

    # (MaxN) Allow for, and filter out, alerts we'd expect to see in an AIO environment.
    #        TODO - find a way of configuring this for SCT running in other environments.
    aio_alerts_to_ignore = [
        # We know our volumes are small.
        { "alertname": "StorageFillingUp" },
        { "alertname": "ElasticsearchDiskSpaceLow" },
        # This is probably due to storage space..
        { "alertname": "ElasticsearchClusterYellow" },
        # ..or because we're running in a single instance and it wants to be clustered across multiple nodes.
        { "alertname": "ElasticsearchUnassignedShards" },
        # It's a small AIO!
        { "alertname": "LowMemory" },
        # It's only one node and expects three, see https://github.com/stackhpc/stackhpc-kayobe-config/pull/1579
        { "alertname": "RabbitMQNodeDown" },
        # This is probably because Tempest runs before pytest so the container has been recently stopped.
        { "alertname": "ContainerKilled", "name": "tempest" },
        # This alert sometimes triggers after periods of high activity e.g. a major upgrade
        { "alertname": "RabbitMQTooMuchReady" },
    ]

    def alert_is_ignored(alert, alerts_to_ignore):
        # Check if any of the "ignore cases" match the alert
        return any(alert_to_ignore.items() <= alert.items() for alert_to_ignore in alerts_to_ignore)

    alerts = [ alert for alert in alerts if not alert_is_ignored(alert["labels"], aio_alerts_to_ignore) ]
    assert len(alerts) == 0
