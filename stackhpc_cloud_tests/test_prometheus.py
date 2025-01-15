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


def test_prometheus_connection(prom):
    """Check that Prometheus is accessible."""
    assert prom.check_prometheus_connection()


def test_prometheus_node_exporter_metrics(prom):
    """Check that expected node exporter metrics exist."""
    metrics = prom.all_metrics()
    assert "node_cpu_seconds_total" in metrics
