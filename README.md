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
