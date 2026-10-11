# Agreed design

The image adds Cloudflare DNS validation to Caddy Docker Proxy so certificate
renewal does not require inbound access through the UCG Ultra's region blocking.

- Public repository: `cf1331/caddy-docker-proxy-cloudflare`.
- Public image: `ghcr.io/cf1331/caddy-docker-proxy-cloudflare`.
- Support Linux AMD64 and ARM64 using free standard GitHub runners.
- Build with the official Caddy builder. Replace the executable in upstream
  Docker Proxy's scratch runtime with a statically linked build containing
  Docker Proxy and Cloudflare DNS. Keep its certificates and runtime defaults.
- Pin Caddy, Docker Proxy, Cloudflare, base image digests, and build actions.
- Hosted Renovate detects numbered version and image updates. Exclude prereleases
  and development branch commits. No custom scheduled polling service.
- Automatically merge patch, minor, and digest updates after required image
  checks pass. Major upgrades require review. Cloudflare minor upgrades below
  version 1.0 also require review.
- Verify each architecture's versions, required modules, Cloudflare configuration,
  and an HTTP request routed from Docker labels before publishing that image.
- Publish a multi-platform `latest` only when both architectures pass. Keep
  `sha-<full commit>-<run>-<attempt>` tags for rollback, including reruns of the
  same commit. Failed checks preserve the previous
  `latest` image.
- Dockhand controls deployment. Do not change the live server in this task.
- Cloudflare credentials remain on the server and are unnecessary for CI.
- Initial setup includes the public repository/package, required branch checks,
  and enabling hosted Renovate for this repository.

Live DNS-01 issuance and renewal must be verified when deploying the image.
