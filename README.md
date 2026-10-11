# Caddy Docker Proxy with Cloudflare DNS

Caddy with Docker-label configuration and Cloudflare DNS-01 validation, in the
upstream Docker Proxy scratch runtime. No shell or package manager is included.
Certificate authorities verify DNS records, so inbound region blocking can stay
enabled while Caddy obtains and renews certificates.

## Using the image

Use `ghcr.io/cf1331/caddy-docker-proxy-cloudflare:latest` in your existing Caddy
service. Docker selects the Linux AMD64 or ARM64 image for your server.

Add the Cloudflare token to the **Caddy container's environment** and configure the
global option through labels on that container:

```yaml
services:
  caddy:
    image: ghcr.io/cf1331/caddy-docker-proxy-cloudflare:latest
    environment:
      CLOUDFLARE_API_TOKEN: ${CLOUDFLARE_API_TOKEN:?Set the Cloudflare API token}
    labels:
      caddy.acme_dns: "cloudflare {env.CLOUDFLARE_API_TOKEN}"
```

This is a fragment for your existing Compose service. Keep its networks, ports,
Docker access, and persistent `/data` and `/config` mounts. Keep existing application
labels. Store the token in Dockhand's secret configuration, never in Git or an image.
The token needs `Zone:Zone:Read` and `Zone:DNS:Edit` for the DNS zones Caddy manages.
Those zones must be hosted in Cloudflare, or the ACME challenge must be delegated
to a Cloudflare-hosted zone.

Outbound ACME, Cloudflare API, and DNS access is still required. This plugin uses
Cloudflare for DNS validation and does not require proxying web traffic through
Cloudflare.

Dockhand controls deployment. Check the container logs for successful DNS-01
issuance after switching images. Existing certificates can delay that validation
until their next renewal. Shell-based health checks such as `curl` must be changed
for this scratch image. Caddy commands still work through `docker exec`.

## Updates

Hosted [Renovate](https://github.com/apps/renovate) checks for new versions of Caddy,
Docker Proxy, Cloudflare DNS, base image digests, and build actions. Caddy and Docker
Proxy versions come from the pinned official builder and Docker Proxy runtime
references in the Dockerfile. Cloudflare version tags are checked directly because the project
does not publish GitHub Releases.

Patch, minor, and digest updates automatically merge after the required AMD64 and
ARM64 image checks pass. Major upgrades remain open for review. Cloudflare minor
upgrades below 1.0 also remain open for review. Prereleases and development commits
are excluded. A Docker Proxy major upgrade may also require changing the Go
module's `/v2` import path.

Every successful build on `main` publishes `latest` and
`sha-<full commit>-<run>-<attempt>` tags. The run and attempt numbers prevent a
rebuild of the same commit from overwriting an earlier rollback image.
Both architectures must pass before `latest` is updated. Failed checks preserve
the existing `latest`. To roll back, set the service image to a previous
`sha-<full commit>-<run>-<attempt>` tag, or its registry digest.

Standard GitHub runners and hosted Renovate are free for this public repository.
GitHub Container Registry storage and bandwidth are currently free.

## Build and verify locally

```sh
docker build --tag caddy-cloudflare:test .
python3 tests/verify_image.py caddy-cloudflare:test amd64
```

Use `arm64` on an ARM64 host. Verification checks the architecture, pinned versions,
modules, Cloudflare configuration using a fake token, absence of a shell, and a
real HTTP request routed using Docker labels. It creates temporary containers and
a network, then removes them. It does not request certificates or use real secrets.

## Repository setup

1. Enable [hosted Renovate](https://github.com/apps/renovate/installations/new) for
   this repository. The existing `renovate.json` supplies the update policy.
2. Protect `main` with required checks `Image checks (amd64)` and
   `Image checks (arm64)`, requiring branches to be current before merging.
   Do not require reviews for every update, because that blocks routine automerge.
3. Make the GHCR package public after its first publication. A public repository
   does not automatically make a newly created package public.

The GitHub workflow uses its repository token to publish, so no registry password
or Cloudflare token is needed in repository secrets. Failed builds and updates
are visible in Actions, Renovate PRs, and its Dependency Dashboard.
