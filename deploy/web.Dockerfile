# NeoMortalSurv web image: Caddy with the built frontend. Build from the repository root:
#
#     docker build -f deploy/web.Dockerfile -t neomortalsurv-web .
#
# VITE_ENABLE_KK=true adds Kazakh (docs/REBUILD_SPEC.md 7.5). The compose file passes
# true since the review reported on 2026-11-13; a bare `docker build` leaves it out.
FROM node:26-alpine AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts
COPY frontend/ ./
ARG VITE_ENABLE_KK=false
ENV VITE_ENABLE_KK=$VITE_ENABLE_KK
RUN npm run build

FROM caddy:2-alpine
# Non-root. The caddy binary carries the capability to bind ports 80 / 443; the data and
# config directories (certificates) must belong to the user before volumes are created.
RUN adduser -D -H -u 10002 web && mkdir -p /data /config /etc/caddy/legacy && chown -R web:web /data /config
COPY deploy/Caddyfile /etc/caddy/Caddyfile
COPY --from=build /src/dist /srv
USER web
