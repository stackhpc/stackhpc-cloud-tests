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

# TODO:
# * Cluster health

from opensearchpy import OpenSearch
import os
import pytest
import requests

from stackhpc_cloud_tests import utils


@pytest.fixture
def opensearch() -> OpenSearch:
    """Pytest fixture that creates an OpenSearch API client."""
    # https://opensearch.org/docs/latest/clients/python-low-level/
    opensearch_hosts = os.environ["OPENSEARCH_HOSTS"].split(",")
    opensearch_port = os.environ["OPENSEARCH_PORT"]
    opensearch_hosts = [
        {"host": host, "port": opensearch_port} for host in opensearch_hosts
    ]
    opensearch_tls = utils.str_to_bool(os.environ["OPENSEARCH_TLS"])
    if opensearch_tls:
        opensearch_verify_certs = utils.str_to_bool(
            os.environ["OPENSEARCH_VERIFY_CERTS"]
        )
    else:
        opensearch_verify_certs = True
    return OpenSearch(
        hosts=opensearch_hosts,
        http_compress=True,
        use_ssl=opensearch_tls,
        verify_certs=opensearch_verify_certs,
        ssl_show_warn=False,
    )


def test_opensearch_has_info_logs(opensearch):
    """Check that OpenSearch has some INFO level logs."""
    query = {
        "query": {
            "match": {
                "log_level": "INFO",
            }
        }
    }
    # https://opensearch-project.github.io/opensearch-py/api-ref/clients/opensearch_client.html#opensearchpy.OpenSearch.search
    result = opensearch.search(body=query, index="flog-*", size=1)
    assert len(result["hits"]["hits"]) == 1


def test_opensearch_dashboards_status():
    """Check that OpenSearch Dashboards is accessible and is in a green state."""
    dashboard_url = os.environ["OPENSEARCH_DASHBOARDS_URL"]
    dashboard_username = os.environ["OPENSEARCH_DASHBOARDS_USERNAME"]
    dashboard_password = os.environ["OPENSEARCH_DASHBOARDS_PASSWORD"]
    dashboard_url += "/api/status"
    dashboard_cacert = os.environ.get("OPENSEARCH_DASHBOARDS_CACERT")
    kwargs = {}
    if dashboard_cacert:
        kwargs["verify"] = dashboard_cacert
    result = requests.get(dashboard_url, auth=(dashboard_username, dashboard_password), **kwargs)
    assert result.ok
    result = result.json()
    assert result["status"]["overall"]["state"] == "green"
