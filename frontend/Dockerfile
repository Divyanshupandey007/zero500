# Stage 1: build — install deps and compile the Angular application.
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies with ci for reproducible, locked builds.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Compile the Angular application (outputs to dist/frontend/browser).
COPY frontend/ ./
RUN npm run build

# Stage 2: serve — lightweight nginx serving the static files.
FROM nginx:1.27-alpine

# Remove the default nginx static assets and copy the Angular build.
RUN rm -rf /usr/share/nginx/html/*
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html

# SPA fallback: route every request to index.html so direct URLs work.
COPY frontend/public/_redirects /etc/nginx/conf.d/angular-redirects.conf
RUN sed -i 's|#include /etc/nginx/conf.d/\*.conf;|include /etc/nginx/conf.d/*.conf;|' \
    /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
