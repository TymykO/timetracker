# Stage development: dla dev z hot-reload
FROM node:20-alpine as development

# Ustaw working directory
WORKDIR /app

# Skopiuj package files
COPY frontend/package*.json ./

# Zainstaluj dependencies
RUN npm install

# Skopiuj resztę kodu
COPY frontend/ ./

# Expose Vite dev server port
EXPOSE 5173

# CMD dla development
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# Stage builder: budowanie produkcyjnej wersji
FROM node:20-alpine as builder

WORKDIR /app

# Skopiuj package files i zainstaluj dependencies
COPY frontend/package*.json ./
RUN npm install

# Skopiuj kod źródłowy
COPY frontend/ ./

# Build argument dla API URL
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Zbuduj aplikację
RUN npm run build

# Stage production: nginx z zbudowaną aplikacją
FROM nginx:alpine as production

# Skopiuj zbudowane pliki z builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Skopiuj custom nginx config dla SPA routing
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 80
EXPOSE 80

# CMD domyślny nginx
CMD ["nginx", "-g", "daemon off;"]
