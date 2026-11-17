# Caddy com o módulo de limite de pedidos (não vem no Caddy padrão). Ambos Apache-2.0.
FROM caddy:2.11.9-builder AS build
RUN xcaddy build --with github.com/mholt/caddy-ratelimit@5625512f24f6f59d6f64fb3aafe5eecff0b286db

FROM caddy:2.11.9
COPY --from=build /usr/bin/caddy /usr/bin/caddy
