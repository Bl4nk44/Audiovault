# Build Stage
FROM node:25-alpine AS build

ARG APP_VERSION=0.9.0
ENV VITE_APP_VERSION=${APP_VERSION}

WORKDIR /app

# Copy VERSION file from root context
COPY VERSION ./VERSION

# Copy frontend package files first for better caching
COPY frontend/package*.json ./

# Install dependencies with retry logic
RUN npm ci --prefer-offline --no-audit || npm ci --prefer-offline --no-audit

# Copy remaining frontend code
COPY frontend/ ./

# Build frontend
RUN npm run build

# Production Stage
FROM nginx:alpine AS production

# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Support running as non-root
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid /usr/share/nginx/html /var/cache/nginx /etc/nginx/conf.d

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
