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
    if "tls" in skip_tls:
        skip = True

if os.environ.get("SKIP_FRONTENDS") is not None:
    skip_frontends = os.environ.get("SKIP_FRONTENDS")
    skip_frontends = skip_frontends.split(",")
else:
    skip_frontends = []

if os.environ.get("SKIP_BACKENDS") is not None:
    skip_backends = os.environ.get("SKIP_BACKENDS")
    skip_backends = skip_backends.split(",")
else:
    skip_backends = []

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
    # get ports for frontend addr population
    ports = {}
    for be in backends:
        name = be["pxname"].replace("\n","")
        if "_external_back" in name:
            name = name.replace("_external_back", "_external_front")
        elif "_back" in name:
            name = name.replace("_back", "_front")
        port = be["addr"].split(":")[1]
        ports.update({name: port})
    # populate frontend addresses
    for fe in frontends:
        name = fe["pxname"].replace("\n","")
        if name in ["stats", "metrics", "status"]:
            continue
        if "_front" in name:
            ip = os.environ.get("KOLLA_INTERNAL_VIP")
        elif "_external_front" in name:
            ip = os.environ.get("KOLLA_EXTERNAL_VIP")
        else:
            ip = ""
        try:
            fe["addr"] = f"{ip}:{ports[name]}"
        except KeyError:
            continue
    return frontends,backends

@pytest.mark.skipif(skip, reason="TLS tests skipped.")
def test_tls_frontend(haproxy_info):
    frontends,_ = haproxy_info
    context = ssl.create_default_context()
    for fe in frontends:
        name = fe["pxname"].replace("\n","")
        addr = fe["addr"]
        if name in skip_frontends:
            print("Skipping frontend: ", name)
            continue
        print("Checking frontend: ", name, addr)
        try:
            with socket.create_connection((addr.split(":")[0], int(addr.split(":")[1]))) as sock:
                assert context.wrap_socket(sock, server_hostname=addr.split(":")[0])
                sock.close()
        except Exception as e:
            print(f"TLS handshake failed for frontend: {name}, exception: {e}")
            continue
        print("Success!\n")

@pytest.mark.skipif(skip, reason="TLS tests skipped.")
def test_tls_backend(haproxy_info):
    _,backends = haproxy_info
    context = ssl.create_default_context()
    for be in backends:
        name = be["pxname"].replace("\n","")
        addr = be["addr"]
        if name in skip_backends:
            print("Skipping backend: ", name)
            continue
        print("Checking backend: ", name, addr)
        try:
            with socket.create_connection((addr.split(":")[0], int(addr.split(":")[1]))) as sock:
                assert context.wrap_socket(sock, server_hostname=addr.split(":")[0])
                sock.close()
        except Exception as e:
            print(f"TLS handshake failed for backend: {name}, exception: {e}")
            continue
        print("Success!\n")
