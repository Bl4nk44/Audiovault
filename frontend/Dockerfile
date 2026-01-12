# Build Stage
FROM node:25-alpine AS build

ARG APP_VERSION=0.9.0
ENV VITE_APP_VERSION=${APP_VERSION}

WORKDIR /app

# Copy VERSION file from root context
COPY VERSION ./VERSION

# Copy frontend code
COPY frontend/ ./

# Install dependencies
RUN npm ci

# Build frontend
RUN npm run build

# Production Stage
FROM nginx:alpine AS production

# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
