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

"""Helpers for running Ceph commands against a cephadm deployed cluster.

These tests run on the Ceph monitor hosts, which cephadm labels "_admin" and
therefore hold /etc/ceph/ceph.conf and the client.admin keyring. The Ceph CLI
is not installed on the host, so commands are run inside a container via
"cephadm shell", which requires root.
"""

import json
import os

# Cache added considering the starting cost of "cephadm shell" container is
# roughly 15 seconds with 30 seconds pytest test timeouts. This cache
# cannot observe change over time. Its one consistent view over the whole run.
_COMMAND_CACHE = {}


def should_skip(test_tag):
    """Return whether tests with the given tag should be skipped.
    Tests are skipped by listing their tag in the SKIP_SCT environment
    variable, e.g. SKIP_SCT=ceph-health,ntp.
    """
    return test_tag in os.environ.get("SKIP_SCT", "")


def count_from_env(env_var):
    """Return a daemon count from the environment, or None if it is unset.
    """
    value = os.environ.get(env_var)
    if not value:
        return None
    return int(value)


def list_from_env(env_var):
    """Return a comma separated environment variable as a list of strings.
    """
    value = os.environ.get(env_var)
    if not value:
        return []

    items = []
    for item in value.split(","):
        item = item.strip()
        if item:
            items.append(item)
    return items


def json_from_env(env_var):
    """Return a JSON encoded environment variable as Python data.
    Returns None when unset, so callers can skip checks the deployment
    has not supplied expectations for.
    """
    value = os.environ.get(env_var)
    if not value:
        return None
    return json.loads(value)


def run_ceph(host, ceph_args):
    """Run "ceph <ceph_args>" inside a cephadm shell.
    """
    if ceph_args not in _COMMAND_CACHE:
        _COMMAND_CACHE[ceph_args] = host.run(f"cephadm shell -- ceph {ceph_args}")
    return _COMMAND_CACHE[ceph_args]


def _extract_json(command_output):
    """Return the JSON document from the output of a cephadm shell command,
    without being dependant on cephadm's choice of stream.
    """
    # A JSON document starts with "{" or "[". Anything before that is
    # cephadm progress output, so skip over it.
    for index, character in enumerate(command_output):
        if character in "{[":
            return command_output[index:]

    raise ValueError(f"No JSON found in cephadm output: {command_output}")


def run_ceph_json(host, ceph_args):
    """Run "ceph <ceph_args> -f json" in a cephadm shell and parse the output.
    """
    result = run_ceph(host, f"{ceph_args} -f json")
    message = f"'ceph {ceph_args}' failed with code {result.rc}: {result.stderr}"
    assert result.rc == 0, message

    return json.loads(_extract_json(result.stdout))
