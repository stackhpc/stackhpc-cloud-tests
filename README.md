# StackHPC Cloud Tests

Automated testing for StackHPC OpenStack Clouds.

Provides test coverage of various aspects of OpenStack and related services, including:

* OpenSearch
* Prometheus

Tests are written using [pytest](https://docs.pytest.org/).

## Installation

Clone this repository.

Create a virtual environment.

```sh
python3 -m venv venv
```

Install stackhpc-cloud-tests and its dependencies.

```sh
venv/bin/pip install <path/to/repo> -r <path/to/repo>/requirements.txt
```

## Usage

Run all tests provided.

```sh
py.test --pyargs stackhpc_cloud_tests
```

Or run tests from a specific submodule.

```sh
py.test --pyargs stackhpc_cloud_tests.test_prometheus
```

To skip specific tests, set the SKIP_SCT variable:
| Test to skip  | SKIP_SCT value |
|---------------|----------------|
|test_docker.py | docker         |
|test_ntp.py    | ntp            |
|test_selinux.py| selinux        |
|test_grafana.py| grafana        |
|test_opensearch.py| opensearch  |
|test_prometheus.py| prometheus  |

To skip more than one test, set SKIP_SCT to a comma separated list:
```sh
# Skip both test_docker.py and test_ntp.py
export SKIP_SCT=docker,ntp
```
