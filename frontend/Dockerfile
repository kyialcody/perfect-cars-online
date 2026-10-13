# Prod image: build the SPA, then serve the static bundle with nginx.
# nginx also reverse-proxies /api to the backend, so the frontend talks to the
# API same-origin (no CORS, works by IP now and by domain later without rebuild).
FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Baked at build time. Default to a relative /api (proxied by nginx) and the
# Russia brand until the real domains resolve the brand by hostname.
# VITE_YANDEX_MAPS_API_KEY is a client-side key (embedded in the browser bundle,
# restricted by referrer), passed in from .env at build time.
ARG VITE_API_URL=/api
ARG VITE_BRAND=perfect-cars
ARG VITE_YANDEX_MAPS_API_KEY=
ENV VITE_API_URL=$VITE_API_URL \
    VITE_BRAND=$VITE_BRAND \
    VITE_YANDEX_MAPS_API_KEY=$VITE_YANDEX_MAPS_API_KEY

RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
