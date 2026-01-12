# Build Stage
FROM node:25-alpine AS build

WORKDIR /app

# Copy entire project first
COPY . .

# Install dependencies for frontend
RUN npm ci

# Build frontend
RUN npm run build

# Production Stage
FROM nginx:alpine AS production

# Copy built assets from builder
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
