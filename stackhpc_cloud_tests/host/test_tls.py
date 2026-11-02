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
import docker
import socket
import ssl

skip = False
if os.environ.get("SKIP_TLS") is not None:
    skip_tls = os.environ.get("SKIP_TLS")
    if "docker" in skip_tls:
        skip = True

@pytest.fixture
def haproxy_info():
    cmd = "sh -c \"echo 'show stat' | socat stdio /var/lib/kolla/haproxy/haproxy.sock\""
    client = docker.from_env()
    haproxy_container = client.containers.get("haproxy")
    rc, res = haproxy_container.exec_run(cmd)
    res = res.decode().split(",")
    res = res[:-1]
    fields = res[:res.index("\nstats")]
    fields[0] = fields[0][2:]
    haproxy_info = [{fields[i]:res[i+len(fields)+j] for i in range(0,len(fields)-1)} for j in range(0,len(res)-len(fields),len(fields))]
    frontends = [entry for entry in haproxy_info if entry["type"] == "0"]
    backends = [entry for entry in haproxy_info if entry["type"] == "2"]
    return frontends,backends

@pytest.mark.skipif(skip, reason="TLS tests skipped.")
def test_tls_frontend(haproxy_info):
    frontends,_ = haproxy_info
    with ssl.create_default_context() as context:
        for fe in frontends:
            print("Checking backend: ", fe["pxname"], fe["addr"])
            with socket.create_connection((fe["addr"].split(":")[0], int(fe["addr"].split(":")[1]))) as sock:
                assert context.wrap_socket(sock, server_hostname=fe["addr"].split(":")[0])
                sock.close()
            print("Success!\n")

@pytest.mark.skipif(skip, reason="TLS tests skipped.")
def test_tls_backend(haproxy_info):
    _,backends = haproxy_info
    with ssl.create_default_context() as context:
        for be in backends:
            print("Checking backend: ", be["pxname"], be["addr"])
            with socket.create_connection((be["addr"].split(":")[0], int(be["addr"].split(":")[1]))) as sock:
                assert context.wrap_socket(sock, server_hostname=be["addr"].split(":")[0])
                sock.close()
            print("Success!\n")