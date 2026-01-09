# Build Stage
FROM node:22-alpine AS build

WORKDIR /app

# Copy entire project first
COPY . .

# Install dependencies for frontend
WORKDIR /app/frontend
RUN npm ci

# Build frontend
RUN npm run build

# Production Stage
FROM nginx:alpine AS production

# Copy built assets from builder
COPY --from=build /app/frontend/dist /usr/share/nginx/html

# Copy custom nginx config
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
