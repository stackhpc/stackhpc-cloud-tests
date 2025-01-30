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

# TODO: Check if we can validate that dashboards load correctly.

from grafana_client import GrafanaApi
import os
import pytest


@pytest.fixture
def grafana() -> GrafanaApi:
    """Pytest fixture that creates a Grafana API client."""
    # https://github.com/grafana-toolbox/grafana-client
    grafana_url = os.environ["GRAFANA_URL"]
    grafana_username = os.environ["GRAFANA_USERNAME"]
    grafana_password = os.environ["GRAFANA_PASSWORD"]
    return GrafanaApi.from_url(
        grafana_url,
        credential=(grafana_username, grafana_password),
    )


def test_grafana_api_stats(grafana):
    """Test that Grafana API stats are accessible."""
    # https://grafana.com/docs/grafana/latest/developers/http_api/admin/#grafana-stats
    result = grafana.admin.stats()
    assert result["dashboards"] > 0
    assert result["datasources"] > 0
