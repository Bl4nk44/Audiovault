# Build Stage
FROM node:22-slim as build

WORKDIR /app

COPY package*.json ./
# Clean install for reproducible builds
COPY VERSION /VERSION

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

# Production Stage
FROM nginx:alpine as production

# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
