"""Check the published image's public interfaces using a local Docker engine."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid


def docker(*args, check=True):
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, check=False
    )
    if check and result.returncode:
        raise RuntimeError(f"docker {args}:\n{result.stdout}\n{result.stderr}")
    return result


def verify(image, architecture):
    root = Path(__file__).resolve().parent.parent
    modules = docker("run", "--rm", image, "list-modules").stdout.splitlines()
    assert "docker_proxy" in modules, "Docker Proxy module missing"
    assert "dns.providers.cloudflare" in modules, "Cloudflare DNS module missing"
    metadata = json.loads(docker("image", "inspect", image).stdout)[0]
    assert metadata["Os"] == "linux" and metadata["Architecture"] == architecture, (
        "Unexpected image architecture"
    )
    assert metadata["Config"]["Entrypoint"] == ["/bin/caddy"], "Unexpected entrypoint"
    assert metadata["Config"]["Cmd"] == ["docker-proxy"], "Unexpected default command"
    dockerfile = (root / "Dockerfile").read_text()
    versions = dict(re.findall(r"^ARG (\w+)=(\S+)$", dockerfile, re.M))
    caddy_version = re.search(r"^FROM caddy:([^\s]+)-builder@", dockerfile, re.M)[1]
    assert docker("run", "--rm", image, "version").stdout.split()[0] == (
        "v" + caddy_version
    ), "Caddy version differs from the pinned version"
    dependencies = {}
    for line in docker("run", "--rm", image, "build-info").stdout.splitlines():
        parts = line.split()
        if parts and parts[0] == "dep":
            dependencies[parts[1]] = parts[2]
    assert dependencies["github.com/lucaslorentz/caddy-docker-proxy/v2"] == (
        "v" + versions["CADDY_DOCKER_PROXY_VERSION"]
    ), "Docker Proxy version differs from the pinned version"
    assert dependencies["github.com/caddy-dns/cloudflare"] == versions["CLOUDFLARE_VERSION"], (
        "Cloudflare version differs from the pinned version"
    )
    print("Pinned versions and required modules verified", flush=True)

    prefix = "caddy-image-check-" + uuid.uuid4().hex[:10]
    config, backend, proxy = (prefix + suffix for suffix in ("-config", "-backend", "-proxy"))
    network = prefix + "-network"
    token = "a" * 40  # Valid format, not a real Cloudflare credential.
    try:
        docker("create", "--name", config, "--env", "CLOUDFLARE_API_TOKEN=" + token,
               image, "validate", "--config", "/Caddyfile", "--adapter", "caddyfile")
        docker("cp", str(root / "tests/fixtures/cloudflare.Caddyfile"), config + ":/Caddyfile")
        docker("start", "--attach", config)
        state = json.loads(docker("inspect", config).stdout)[0]["State"]
        assert state["ExitCode"] == 0, "Cloudflare configuration validation failed"
        with tempfile.TemporaryDirectory() as temporary:
            shell = docker("cp", config + ":/bin/sh", str(Path(temporary) / "sh"), check=False)
            assert shell.returncode != 0 and "Could not find the file" in shell.stderr, (
                "Runtime unexpectedly contains a shell, or its filesystem could not be checked"
            )
        print("Cloudflare configuration and shell-free runtime verified", flush=True)

        docker("network", "create", network)
        docker("create", "--name", backend, "--network", network,
               "--label", "caddy=http://proxy.test:8080",
               "--label", "caddy.reverse_proxy={{upstreams 80}}",
               image, "run", "--config", "/Caddyfile", "--adapter", "caddyfile")
        docker("cp", str(root / "tests/fixtures/backend.Caddyfile"), backend + ":/Caddyfile")
        docker("start", backend)
        docker("run", "--detach", "--name", proxy, "--network", network,
               "--publish", "127.0.0.1::8080",
               "--volume", "/var/run/docker.sock:/var/run/docker.sock:ro",
               "--env", "CADDY_INGRESS_NETWORKS=" + network,
               "--env", "CLOUDFLARE_API_TOKEN=" + token,
               "--label", "caddy.acme_dns=cloudflare {env.CLOUDFLARE_API_TOKEN}", image)
        address = docker("port", proxy, "8080/tcp").stdout.strip()
        request = urllib.request.Request("http://" + address, headers={"Host": "proxy.test"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                with opener.open(request, timeout=2) as response:
                    assert response.read().decode() == "Docker labels route requests", (
                        "Unexpected response through Docker Proxy"
                    )
                print("HTTP request routed from Docker labels", flush=True)
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(1)
        else:
            raise AssertionError("Docker Proxy did not route a request within 45 seconds")
    except Exception:
        for container in (config, backend, proxy):
            logs = docker("logs", container, check=False)
            print(logs.stdout + logs.stderr, file=sys.stderr)
        raise
    finally:
        docker("rm", "--force", config, backend, proxy, check=False)
        docker("network", "rm", network, check=False)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[2] not in ("amd64", "arm64"):
        raise SystemExit("Usage: python tests/verify_image.py IMAGE amd64|arm64")
    verify(sys.argv[1], sys.argv[2])
