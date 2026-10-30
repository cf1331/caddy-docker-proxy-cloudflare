ARG CADDY_DOCKER_PROXY_VERSION=2.13.1
# renovate: datasource=github-tags depName=caddy-dns/cloudflare
ARG CLOUDFLARE_VERSION=v0.2.4

FROM caddy:2.11.7-builder@sha256:c4cd20eaa0b69112fd5d4f721ffc9671687e1d5d0b155c8620cf7546dbef94c0 AS builder
ARG CADDY_DOCKER_PROXY_VERSION
ARG CLOUDFLARE_VERSION
RUN CGO_ENABLED=0 XCADDY_SETCAP=0 xcaddy build ${CADDY_VERSION} \
    --with github.com/lucaslorentz/caddy-docker-proxy/v2@v${CADDY_DOCKER_PROXY_VERSION} \
    --with github.com/caddy-dns/cloudflare@${CLOUDFLARE_VERSION}

FROM lucaslorentz/caddy-docker-proxy:${CADDY_DOCKER_PROXY_VERSION}@sha256:4c14f2ddb9c259903c464ac0423c936b10757bda7c57f8eb34b93efa903c8b8d
COPY --from=builder /usr/bin/caddy /bin/caddy
LABEL org.opencontainers.image.source="https://github.com/cf1331/caddy-docker-proxy-cloudflare"
