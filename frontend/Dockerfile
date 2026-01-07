# Build Stage
FROM node:22-alpine AS build

WORKDIR /app

# Copy frontend source and dependencies
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# Production Stage
FROM nginx:alpine AS production

# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
